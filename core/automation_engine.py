import json
import threading
import time
from datetime import datetime

class AutomationEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print("[Automation] Engine started")

    def _run_scheduler(self):
        while self.running:
            try:
                self.check_scheduled_automations()
            except Exception as e:
                print(f"[Automation] Error in scheduler: {e}")
            time.sleep(60)  # Check every minute

    def check_scheduled_automations(self):
        conn = self.db_manager.get_connection()
        c = conn.cursor()
        try:
            # Get active scheduled automations
            c.execute("SELECT id, config, last_run FROM se_automations WHERE type = 'scheduled' AND enabled = 1")
            rows = c.fetchall()
            
            now = datetime.now()
            current_weekday = now.strftime('%A').lower()
            current_time = now.strftime('%H:%M')
            
            for row in rows:
                auto_id = row[0]
                config = json.loads(row[1]) if row[1] else {}
                last_run = row[2]
                
                # Check if it should run
                should_run = False
                
                freq = config.get('frequency', 'weekly')
                target_time = config.get('time', '09:00')
                target_day = config.get('day', 'monday').lower()
                
                # Simple check: if current time matches target time
                # And if it hasn't run today (or recently)
                
                if current_time == target_time:
                    if freq == 'daily':
                        should_run = True
                    elif freq == 'weekly' and current_weekday == target_day:
                        should_run = True
                    elif freq == 'monthly' and now.day == 1: # Simplified monthly
                        should_run = True
                
                # Prevent double run in the same minute if loop is fast, 
                # but we sleep 60s so it might be fine. 
                # Better: check if last_run was today
                if should_run and last_run:
                    last_run_dt = datetime.strptime(last_run, '%Y-%m-%d %H:%M:%S')
                    if last_run_dt.date() == now.date():
                        should_run = False

                if should_run:
                    print(f"[Automation] Running scheduled automation {auto_id}")
                    # For scheduled, we might need to check all products for low stock?
                    # Or just create a placeholder import?
                    # The UI implies "Automatically import on schedule".
                    # Let's assume it checks for low stock products and orders them.
                    self.execute_scheduled_import(auto_id, config)
                    
                    # Update last_run
                    c.execute("UPDATE se_automations SET last_run = ? WHERE id = ?", 
                              (now.strftime('%Y-%m-%d %H:%M:%S'), auto_id))
                    conn.commit()
                    
        except Exception as e:
            print(f"[Automation] Error checking scheduled: {e}")
        finally:
            conn.close()

    def check_low_stock(self, product_id, current_stock):
        """Called when stock changes"""
        conn = self.db_manager.get_connection()
        c = conn.cursor()
        try:
            # Get active low_stock automations
            c.execute("SELECT id, config FROM se_automations WHERE type = 'low_stock' AND enabled = 1")
            rows = c.fetchall()
            
            for row in rows:
                auto_id = row[0]
                config = json.loads(row[1]) if row[1] else {}
                
                scope = config.get('product_id', 'all')
                threshold = int(config.get('threshold', 10))
                
                should_trigger = False
                if scope == 'all':
                    if current_stock < threshold:
                        should_trigger = True
                elif scope == 'category':
                    # Need to check category, but for now skip
                    pass
                elif str(scope) == str(product_id):
                    if current_stock < threshold:
                        should_trigger = True
                
                if should_trigger:
                    print(f"[Automation] Triggering low stock automation {auto_id} for product {product_id}")
                    self.execute_import_automation(auto_id, config, product_id)
                    
                    # Update last_run
                    c.execute("UPDATE se_automations SET last_run = ? WHERE id = ?", 
                              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), auto_id))
                    conn.commit()
                    
        except Exception as e:
            print(f"[Automation] Error checking low stock: {e}")
        finally:
            conn.close()

    def execute_import_automation(self, auto_id, config, product_id):
        # Create an import transaction
        conn = self.db_manager.get_connection()
        c = conn.cursor()
        try:
            reorder_qty = int(config.get('reorder_quantity', 50))
            
            code = f"IMP-AUTO-{auto_id}-{int(time.time())}"
            
            # Get product price to estimate cost (or 0)
            c.execute("SELECT name, import_price FROM products WHERE id = ?", (product_id,))
            prod = c.fetchone()
            unit_price = prod[1] if prod and prod[1] else 0
            total_price = unit_price * reorder_qty
            
            # Use a default supplier (e.g. ID 1) or find one
            c.execute("SELECT id FROM suppliers LIMIT 1")
            supplier = c.fetchone()
            supplier_id = supplier[0] if supplier else 1
            
            c.execute('''INSERT INTO import_transactions 
                            (code, supplier_id, total_amount, status, notes, created_by)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                        (code, supplier_id, total_price, 'pending', f'Auto-generated by automation #{auto_id}', 1)) # 1 is usually admin
            import_id = c.lastrowid
            
            c.execute('''INSERT INTO import_details 
                            (import_id, product_id, quantity, unit_price, total_price)
                            VALUES (?, ?, ?, ?, ?)''',
                        (import_id, product_id, reorder_qty, unit_price, total_price))
            
            conn.commit()
            print(f"[Automation] Created import {code}")
                
        except Exception as e:
            print(f"[Automation] Error executing automation: {e}")
            conn.rollback()
        finally:
            conn.close()

    def execute_scheduled_import(self, auto_id, config):
        # For scheduled import, maybe we check all products below a certain threshold?
        # Or just create a dummy import?
        # Let's implement a "Restock all low stock items" logic for scheduled import
        conn = self.db_manager.get_connection()
        c = conn.cursor()
        try:
            threshold = 20 # Default threshold for scheduled check
            reorder_qty = 50
            
            c.execute("SELECT id, stock_quantity, import_price FROM products WHERE stock_quantity < ?", (threshold,))
            low_stock_products = c.fetchall()
            
            if not low_stock_products:
                return

            code = f"IMP-SCH-{auto_id}-{int(time.time())}"
            
            # Use a default supplier
            c.execute("SELECT id FROM suppliers LIMIT 1")
            supplier = c.fetchone()
            supplier_id = supplier[0] if supplier else 1
            
            total_amount = 0
            items = []
            
            for prod in low_stock_products:
                p_id = prod[0]
                price = prod[2] if prod[2] else 0
                total_amount += price * reorder_qty
                items.append((p_id, reorder_qty, price, price * reorder_qty))
            
            c.execute('''INSERT INTO import_transactions 
                            (code, supplier_id, total_amount, status, notes, created_by)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                        (code, supplier_id, total_amount, 'pending', f'Scheduled Import #{auto_id}', 1))
            import_id = c.lastrowid
            
            for item in items:
                c.execute('''INSERT INTO import_details 
                                (import_id, product_id, quantity, unit_price, total_price)
                                VALUES (?, ?, ?, ?, ?)''',
                            (import_id, item[0], item[1], item[2], item[3]))
            
            conn.commit()
            print(f"[Automation] Created scheduled import {code} with {len(items)} items")
            
        except Exception as e:
            print(f"[Automation] Error executing scheduled automation: {e}")
            conn.rollback()
        finally:
            conn.close()
