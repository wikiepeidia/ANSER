import json
import re
import os
from .google_integration import read_sheet, read_doc, write_doc, write_sheet, send_email
from .make_integration import trigger_webhook
from .services.dl_client import DLClient

def resolve_template(template_str, context):
    """
    Replaces {{nodeId.path}} with actual values from context.
    Example: {{1.data[0][0]}} -> "Alice"
    """
    if not template_str:
        return ""
    
    # --- Direct Object Reference Optimization ---
    # If the template is EXACTLY "{{...}}", return the object directly.
    # This allows passing Lists/Dicts between nodes without stringification issues.
    if isinstance(template_str, str) and template_str.startswith('{{') and template_str.endswith('}}') and template_str.count('{{') == 1:
        path = template_str[2:-2].strip()
        parts = path.split('.')
        node_id = parts[0]
        
        if node_id in context:
            try:
                rest = path[len(node_id):]
                expr = f"ctx['{node_id}']{rest}"
                return eval(expr, {"ctx": context})
            except Exception as e:
                print(f"Direct Template Error: {e}")
                # Fallback to regex replacement if eval fails
                pass

    # If it's a JSON string, try to parse it first to handle structure
    # But we need to resolve strings inside it.
    # Simple approach: Regex replace on the string representation
    
    def replacer(match):
        path = match.group(1) # e.g. "1.data[0][0]"
        parts = path.split('.')
        node_id = parts[0]
        
        if node_id not in context:
            return "null"
            
        value = context[node_id]
        
        # Traverse the rest of the path (very basic implementation)
        # This supports .field but not [index] properly in this simple regex version
        # For a robust solution, we'd use a library like Jinja2
        
        # Hacky support for list access in the string like "data[0]"
        # We will just eval it (DANGEROUS in prod, okay for test PoC)
        try:
            # Construct a python expression: context['1']['data'][0]
            # We need to map the path string to python accessors
            
            # Remove node_id from path
            rest = path[len(node_id):] # e.g. ".data[0][0]"
            
            # Evaluate context[node_id] + rest
            # We wrap context access in a safe way
            expr = f"ctx['{node_id}']{rest}"
            res = eval(expr, {"ctx": context})
            return str(res)
        except Exception as e:
            print(f"Template Error: {e}")
            return "null"

    # Replace {{...}}
    resolved_str = re.sub(r'\{\{(.*?)\}\}', replacer, template_str)
    
    try:
        return json.loads(resolved_str)
    except:
        return resolved_str

def execute_workflow(workflow_data, token_info=None):
    """
    Executes the workflow defined in the JSON data using a topological sort.
    """
    logs = []
    def log(msg):
        print(msg)
        logs.append(msg)

    nodes = {str(n['id']): n for n in workflow_data.get('nodes', [])}
    edges = workflow_data.get('edges', [])
    
    log(f"Executing workflow with {len(nodes)} nodes and {len(edges)} edges.")
    
    # 1. Build Adjacency List and In-Degree Count
    adj_list = {node_id: [] for node_id in nodes}
    parents_map = {node_id: [] for node_id in nodes} # Track parents for flow control
    in_degree = {node_id: 0 for node_id in nodes}
    
    for edge in edges:
        source = str(edge['from'])
        target = str(edge['to'])
        
        if source in adj_list and target in in_degree:
            adj_list[source].append(target)
            parents_map[target].append(source)
            in_degree[target] += 1
            
    # 2. Topological Sort (Kahn's Algorithm)
    queue = [node_id for node_id in nodes if in_degree[node_id] == 0]
    execution_order = []
    
    while queue:
        current_id = queue.pop(0)
        execution_order.append(current_id)
        
        for neighbor in adj_list[current_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    if len(execution_order) != len(nodes):
        return {"status": "error", "message": "Cycle detected in workflow!", "logs": logs}
        
    # 3. Execute Nodes in Order
    context = {} # Stores output of each node: {node_id: output_data}
    node_results = {}
    
    for node_id in execution_order:
        node = nodes[node_id]
        node_type = node['type']
        config = node.get('config', {})
        
        # --- Flow Control Check ---
        # Check if all parents executed successfully
        parents = parents_map[node_id]
        parent_failed = False
        for p_id in parents:
            p_result = node_results.get(p_id, {})
            if p_result.get('status') != 'success':
                parent_failed = True
                break
        
        if parent_failed:
            log(f"Skipping Node {node_id} because parent failed/skipped.")
            node_results[node_id] = {"status": "skipped", "reason": "Parent failed or skipped"}
            continue

        log(f"--- Running Node {node_id} ({node_type}) ---")
        
        try:
            result = None
            
            # --- Node Logic ---
            if node_type == 'google_sheet_read':
                sheet_id = config.get('sheetId', 'dummy_id')
                range_name = config.get('range', 'A1:Z100')
                result = read_sheet(sheet_id, range_name, token_info)

            elif node_type == 'google_sheet_write':
                sheet_id = config.get('sheetId', 'dummy_id')
                range_name = config.get('range', 'A1')
                data_template = config.get('data', '')
                write_mode = config.get('writeMode', 'json') # json, row, single
                use_parent_data = config.get('useParentData', True)

                log(f"[Workflow] Node {node_id} Write Mode: {write_mode}")

                # Resolve data: prefer parent data if configured
                if (use_parent_data or not data_template) and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_data = parent_data
                        log(f"[Workflow] Using parent node ({p_id}) data for write")
                    else:
                        resolved_data = resolve_template(data_template, context)
                        log(f"[Workflow] Parent data empty, using template")
                else:
                    resolved_data = resolve_template(data_template, context)
                    log(f"[Workflow] Raw Template: '{data_template}'")
                
                log(f"[Workflow] Resolved Data: '{resolved_data}' (Type: {type(resolved_data)})")

                data_to_write = []
                method = 'append' # Default method

                if write_mode == 'json':
                    # Expecting a JSON string or a list object
                    if isinstance(resolved_data, str):
                        try:
                            data_to_write = json.loads(resolved_data)
                        except:
                            # Fallback: treat as single cell if JSON fails
                            data_to_write = [[resolved_data]]
                    elif isinstance(resolved_data, list):
                        data_to_write = resolved_data
                    else:
                        data_to_write = [[str(resolved_data)]]

                elif write_mode == 'row':
                    # Append Row (Comma Separated)
                    # "A, B, C" -> [["A", "B", "C"]]
                    if isinstance(resolved_data, str):
                        row_data = [x.strip() for x in resolved_data.split(',')]
                        data_to_write = [row_data]
                    elif isinstance(resolved_data, list):
                        data_to_write = [resolved_data]
                    else:
                        data_to_write = [[str(resolved_data)]]
                    method = 'append'

                elif write_mode == 'column':
                    # Append Column (Newline Separated)
                    # "A\nB\nC" -> [["A"], ["B"], ["C"]]
                    if isinstance(resolved_data, str):
                        # Split by newline
                        rows = resolved_data.split('\n')
                        data_to_write = [[x.strip()] for x in rows if x.strip()]
                    elif isinstance(resolved_data, list):
                        # Assume list of strings -> column
                        data_to_write = [[str(x)] for x in resolved_data]
                    else:
                        data_to_write = [[str(resolved_data)]]
                    method = 'append'

                elif write_mode == 'cell':
                    # Overwrite Single Cell
                    # Just one cell, but we use UPDATE method to overwrite specific range
                    data_to_write = [[str(resolved_data)]]
                    method = 'update'
                
                # Final Safety Check: Ensure list of lists
                if not isinstance(data_to_write, list):
                    data_to_write = [[str(data_to_write)]]
                elif data_to_write and not isinstance(data_to_write[0], list):
                    data_to_write = [data_to_write]
                
                log(f"[Workflow] Writing to Sheet {sheet_id} at {range_name}. Mode: {write_mode}, Method: {method}")
                log(f"[Workflow] Payload: {data_to_write}")

                result = write_sheet(sheet_id, range_name, data_to_write, method=method, token_info=token_info)
                
            elif node_type == 'google_doc_read':
                doc_id = config.get('docId', 'dummy_doc')
                result = read_doc(doc_id, token_info)

            elif node_type == 'google_doc_write':
                doc_id = config.get('docId', 'dummy_doc')
                content_template = config.get('content', '')
                use_parent = config.get('useParentData', True)

                if (use_parent or not content_template) and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_content = parent_data
                        log(f"[Workflow] Write Doc: using parent node ({p_id}) data")
                    else:
                        resolved_content = resolve_template(content_template, context)
                else:
                    resolved_content = resolve_template(content_template, context)

                # Convert dicts/lists to readable string
                if isinstance(resolved_content, (dict, list)):
                    resolved_content = json.dumps(resolved_content, indent=2, ensure_ascii=False)

                result = write_doc(doc_id, str(resolved_content), token_info)
                
            elif node_type == 'make_webhook':
                url = config.get('url', 'http://example.com/webhook')
                method = config.get('method', 'POST')
                body_template = config.get('body', '{}')
                use_parent = config.get('useParentData', False)
                
                # Resolve payload
                if use_parent and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        payload = parent_data
                        log(f"[Workflow] Make webhook: using parent node ({p_id}) data")
                    else:
                        payload = resolve_template(body_template, context)
                else:
                    payload = resolve_template(body_template, context)
                
                if url.startswith("http"):
                    result = trigger_webhook(url, method, payload)
                else:
                    result = {"status": "skipped", "reason": "Invalid URL"}

            elif node_type == 'slack_notify':
                url = config.get('url', '')
                message_template = config.get('message', '')
                use_parent = config.get('useParentData', False)
                
                if use_parent and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_message = parent_data
                        log(f"[Workflow] Slack: using parent node ({p_id}) data")
                    else:
                        resolved_message = resolve_template(message_template, context)
                elif not message_template and parents:
                    p_id = parents[0]
                    resolved_message = context.get(p_id)
                else:
                    resolved_message = resolve_template(message_template, context)
                
                payload = {"text": str(resolved_message)}
                
                if url.startswith("http"):
                    result = trigger_webhook(url, "POST", payload)
                else:
                    result = {"status": "error", "message": "Invalid Slack Webhook URL"}

            elif node_type == 'discord_notify':
                url = config.get('url', '')
                message_template = config.get('message', '')
                use_parent = config.get('useParentData', False)
                
                if use_parent and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_message = parent_data
                        log(f"[Workflow] Discord: using parent node ({p_id}) data")
                    else:
                        resolved_message = resolve_template(message_template, context)
                elif not message_template and parents:
                    p_id = parents[0]
                    resolved_message = context.get(p_id)
                else:
                    resolved_message = resolve_template(message_template, context)
                
                payload = {"content": str(resolved_message)}
                
                if url.startswith("http"):
                    result = trigger_webhook(url, "POST", payload)
                else:
                    result = {"status": "error", "message": "Invalid Discord Webhook URL"}
            
            elif node_type == 'gmail_send':
                to = config.get('to', '')
                subject = config.get('subject', 'Workflow Notification')
                title = config.get('title', '')
                body_template = config.get('body', '')
                use_parent = config.get('useParentData', False)
                
                if use_parent and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_body = parent_data
                        log(f"[Workflow] Gmail: using parent node ({p_id}) data")
                    else:
                        resolved_body = resolve_template(body_template, context)
                elif not body_template and parents:
                    p_id = parents[0]
                    resolved_body = context.get(p_id)
                else:
                    resolved_body = resolve_template(body_template, context)
                
                final_body = str(resolved_body)
                if title:
                    final_body = f"{title}\n\n{final_body}"

                result = send_email(to, subject, final_body, token_info)

            elif node_type == 'filter':
                # Basic Filter Logic
                # Config: { "keyword": "Active" }
                # Checks if ANY string in the parent context contains the keyword
                keyword = config.get('keyword', '')
                
                # Flatten context values to search
                found = False
                if not keyword:
                    found = True # Pass if no keyword
                else:
                    # Search in immediate parents' output
                    for p_id in parents:
                        p_data = context.get(p_id)
                        if str(keyword).lower() in str(p_data).lower():
                            found = True
                            break
                
                if found:
                    result = {"filtered": False, "message": "Condition met"}
                else:
                    # If filter fails, we raise an exception or return a special status?
                    # Let's return a 'stopped' status so children are skipped
                    node_results[node_id] = {"status": "stopped", "reason": "Filter condition failed"}
                    continue

            elif node_type == 'invoice_ocr':
                # Deep Learning OCR Node
                # Config: { "fileUrl": "..." } or use parent output
                file_url = config.get('fileUrl', '')
                
                # If no URL provided, try to find one in parent output
                if not file_url and parents:
                    p_id = parents[0]
                    p_data = context.get(p_id)
                    # Heuristic: check if parent output looks like a URL or file path
                    if isinstance(p_data, str) and (p_data.startswith('http') or p_data.startswith('/')):
                        file_url = p_data
                
                resolved_url = resolve_template(file_url, context)
                
                client = DLClient()
                # For now, we assume resolved_url is a local path or we need to fetch it
                # If it's a local path (e.g. from upload), pass it directly
                if os.path.exists(resolved_url):
                    result = client.detect_invoice(file_path=resolved_url)
                else:
                    # TODO: Handle remote URLs by downloading them first
                    result = {"error": "Remote URL support not implemented yet", "url": resolved_url}

            elif node_type == 'invoice_forecast':
                # Deep Learning Forecast Node
                # Config: { "data": ..., "useParentData": true/false }
                data_template = config.get('data', '')
                use_parent = config.get('useParentData', True)  # Default to using parent data
                
                resolved_data = None
                
                # Auto-pass parent output if configured or if no data template
                if (use_parent or not data_template) and parents:
                    p_id = parents[0]
                    parent_data = context.get(p_id)
                    if parent_data is not None:
                        resolved_data = parent_data
                        log(f"[Forecast] Using parent node ({p_id}) data: {str(resolved_data)[:200]}")
                    else:
                        log(f"[Forecast] Warning: Parent node ({p_id}) returned no data")
                
                # Fallback to template if parent data is empty
                if resolved_data is None and data_template:
                    resolved_data = resolve_template(data_template, context)
                    log(f"[Forecast] Using template data: {str(resolved_data)[:200]}")
                
                # Final fallback: try to build from all parent outputs
                if resolved_data is None and parents:
                    for p_id in parents:
                        p_data = context.get(p_id)
                        if p_data is not None:
                            resolved_data = p_data
                            log(f"[Forecast] Fallback: using parent ({p_id}) data")
                            break
                
                if resolved_data is None:
                    log(f"[Forecast] Error: No data available for forecasting")
                    result = {"error": "No input data for forecasting. Connect a data source node (OCR, Read Sheet, etc.) or provide data manually.", "status": "failed"}
                else:
                    client = DLClient()
                    result = client.forecast_quantity(resolved_data)
                    log(f"[Forecast] Result: {str(result)[:300]}")
                
            else:
                result = {"status": "skipped", "reason": "Unknown node type"}
            
            # Store result
            context[node_id] = result
            node_results[node_id] = {"status": "success", "output": result}
            
        except Exception as e:
            log(f"Error in Node {node_id}: {str(e)}")
            node_results[node_id] = {"status": "error", "error": str(e)}
            # Stop execution on error? For now, yes.
            return {"status": "failed", "node_results": node_results, "error_node": node_id, "logs": logs}

    return {"status": "completed", "node_results": node_results, "logs": logs}
