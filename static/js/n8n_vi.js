/* Vietnamese translation overlay for n8n editor */
(function() {
    const translations = {
        'Execute workflow': 'Chạy workflow',
        'Execute Workflow': 'Chạy Workflow',
        'Workflows': 'Workflows',
        'Editor': 'Trình chỉnh sửa',
        'Executions': 'Lịch sử chạy',
        'Evaluations': 'Đánh giá',
        'Save': 'Lưu',
        'Saved': 'Đã lưu',
        'Saving': 'Đang lưu...',
        'Delete': 'Xóa',
        'Cancel': 'Hủy',
        'Close': 'Đóng',
        'Confirm': 'Xác nhận',
        'Yes': 'Có',
        'No': 'Không',
        'OK': 'OK',
        'Back': 'Quay lại',
        'Next': 'Tiếp theo',
        'Done': 'Xong',
        'Settings': 'Cài đặt',
        'Search': 'Tìm kiếm',
        'Search...': 'Tìm kiếm...',
        'Search nodes...': 'Tìm node...',
        'Filter': 'Lọc',
        'Add tag': 'Thêm tag',
        '+ Add tag': '+ Thêm tag',
        'Add node': 'Thêm node',
        'Add Node': 'Thêm Node',
        'Rename': 'Đổi tên',
        'Duplicate': 'Nhân bản',
        'Copy': 'Sao chép',
        'Paste': 'Dán',
        'Undo': 'Hoàn tác',
        'Redo': 'Làm lại',
        'Disable': 'Tắt',
        'Enable': 'Bật',
        'Active': 'Đang hoạt động',
        'Inactive': 'Không hoạt động',
        'Activated': 'Đã kích hoạt',
        'Deactivated': 'Đã tắt',
        'Published': 'Đã xuất bản',
        'Draft': 'Nháp',
        'Test workflow': 'Chạy thử',
        'Test step': 'Chạy thử bước',
        'Run': 'Chạy',
        'Running': 'Đang chạy...',
        'Success': 'Thành công',
        'Error': 'Lỗi',
        'Failed': 'Thất bại',
        'Waiting': 'Đang chờ',
        'Credential': 'Xác thực',
        'Credentials': 'Xác thực',
        'Create new credential': 'Tạo xác thực mới',
        'Parameters': 'Tham số',
        'Input': 'Đầu vào',
        'Output': 'Đầu ra',
        'No data': 'Không có dữ liệu',
        'No items': 'Không có mục nào',
        'items': 'mục',
        'item': 'mục',
        'Table': 'Bảng',
        'JSON': 'JSON',
        'Schema': 'Schema',
        'HTML': 'HTML',
        'Binary': 'Nhị phân',
        'Logs': 'Nhật ký',
        'of': 'của',
        'true': 'đúng',
        'false': 'sai',
        'Select...': 'Chọn...',
        'Choose...': 'Chọn...',
        'Enter value...': 'Nhập giá trị...',
        'Expression': 'Biểu thức',
        'Fixed': 'Cố định',
        'Add field': 'Thêm trường',
        'Add option': 'Thêm tùy chọn',
        'Add Value': 'Thêm giá trị',
        'Options': 'Tùy chọn',
        'Connections': 'Kết nối',
        'Notes': 'Ghi chú',
        'Add note': 'Thêm ghi chú',
        'Sticky Note': 'Ghi chú',
        'Webhook': 'Webhook',
        'Schedule Trigger': 'Chạy theo lịch',
        'Manual Trigger': 'Chạy thủ công',
        'HTTP Request': 'Gọi API',
        'Code': 'Mã lệnh',
        'IF': 'Nếu',
        'Switch': 'Rẽ nhánh',
        'Merge': 'Gộp',
        'Set': 'Gán giá trị',
        'Function': 'Hàm',
        'No Trigger': 'Không có Trigger',
        'Start': 'Bắt đầu',
        'All': 'Tất cả',
        'None': 'Không',
        'Personal': 'Cá nhân',
        'Overview': 'Tổng quan',
        'Templates': 'Mẫu',
        'Variables': 'Biến',
        'Favorites': 'Yêu thích',
        'Created at': 'Tạo lúc',
        'Updated at': 'Cập nhật lúc',
        'Last run': 'Lần chạy cuối',
        'Created': 'Đã tạo',
        'Updated': 'Đã cập nhật',
        'Name': 'Tên',
        'Status': 'Trạng thái',
        'Actions': 'Hành động',
        'Open': 'Mở',
        'Share': 'Chia sẻ',
        'Move': 'Di chuyển',
        'Import': 'Nhập',
        'Export': 'Xuất',
        'Download': 'Tải xuống',
        'Upload': 'Tải lên',
        'Pin data': 'Ghim dữ liệu',
        'Unpin data': 'Bỏ ghim',
        'Execute node': 'Chạy node',
        'Test node': 'Chạy thử node',
        'Listen for test event': 'Đợi sự kiện thử',
        'Listening for events': 'Đang đợi sự kiện...',
        'Execute previous nodes': 'Chạy các node trước',
        'Fetch events': 'Lấy sự kiện',
        'Problem running workflow': 'Lỗi chạy workflow',
        'Lost connection to the server': 'Mất kết nối server',
        'Problem logging in': 'Lỗi đăng nhập',
        'Workflow saved': 'Đã lưu workflow',
        'Workflow activated': 'Đã kích hoạt workflow',
        'Workflow deactivated': 'Đã tắt workflow',
        'Node deleted': 'Đã xóa node',
        'Nodes': 'Nodes',
        'Popular': 'Phổ biến',
        'New': 'Mới',
        'Recently used': 'Dùng gần đây',
        'Action in an app': 'Hành động trong ứng dụng',
        'Trigger on an event': 'Kích hoạt khi có sự kiện',
        'Add first step': 'Thêm bước đầu tiên',
        'What happens next?': 'Bước tiếp theo là gì?',
        'Send and wait for approval': 'Gửi và chờ phê duyệt',
        'Error workflow': 'Workflow xử lý lỗi',
        'Retry': 'Thử lại',
        'Stop': 'Dừng',
        'Star': 'Yêu thích',
        'Unstar': 'Bỏ yêu thích',

        // Node creator panel
        'What happens next?': 'Bước tiếp theo?',
        'Search nodes...': 'Tìm node...',
        'AI': 'AI',
        'Build autonomous agents, summarize or search documents, etc.': 'Tạo agent tự động, tóm tắt hoặc tìm kiếm tài liệu, v.v.',
        'Action in an app': 'Hành động trong ứng dụng',
        'Do something in an app or service like Google Sheets, Telegram or Notion': 'Thực hiện hành động trong ứng dụng như Google Sheets, Telegram hoặc Notion',
        'Data transformation': 'Chuyển đổi dữ liệu',
        'Manipulate, filter or convert data': 'Thao tác, lọc hoặc chuyển đổi dữ liệu',
        'Flow': 'Luồng xử lý',
        'Branch, merge or loop the flow, etc.': 'Rẽ nhánh, gộp hoặc lặp luồng, v.v.',
        'Core': 'Cơ bản',
        'Run code, make HTTP requests, set webhooks, etc.': 'Chạy code, gọi API, thiết lập webhook, v.v.',
        'Human review': 'Phê duyệt',
        'Request approval via services like Slack and Telegram before making tool calls': 'Yêu cầu phê duyệt qua Slack, Telegram trước khi thực hiện',
        'Add another trigger': 'Thêm trigger',
        'Triggers start your workflow. Workflows can have multiple triggers.': 'Trigger khởi động workflow. Có thể có nhiều trigger.',

        // Node categories
        'Trigger on an event': 'Kích hoạt khi có sự kiện',
        'Action in an app': 'Hành động trong ứng dụng',
        'On app event': 'Khi có sự kiện ứng dụng',
        'On a schedule': 'Theo lịch trình',
        'On a webhook call': 'Khi nhận webhook',
        'Manually': 'Thủ công',
        'On chat message': 'Khi nhận tin nhắn',
        'When called by another workflow': 'Khi được gọi từ workflow khác',
        'When clicking a button': 'Khi bấm nút',

        // Common node names
        'HTTP Request': 'Gọi API',
        'Webhook': 'Webhook',
        'Schedule Trigger': 'Chạy theo lịch',
        'Manual Trigger': 'Chạy thủ công',
        'Code': 'Mã lệnh',
        'IF': 'Điều kiện',
        'Switch': 'Rẽ nhánh',
        'Merge': 'Gộp dữ liệu',
        'Split Out': 'Tách dữ liệu',
        'Loop Over Items': 'Lặp qua từng mục',
        'Set': 'Gán giá trị',
        'Edit Fields': 'Chỉnh sửa trường',
        'Respond to Webhook': 'Trả kết quả Webhook',
        'No Operation': 'Bỏ qua',
        'Wait': 'Chờ',
        'Execute Workflow': 'Chạy Workflow khác',
        'Error Trigger': 'Khi có lỗi',
        'Aggregate': 'Tổng hợp',
        'Sort': 'Sắp xếp',
        'Limit': 'Giới hạn',
        'Remove Duplicates': 'Loại trùng',
        'Compare Datasets': 'So sánh dữ liệu',
        'Summarize': 'Tóm tắt',
        'Send Email': 'Gửi Email',
        'Read/Write Files from Disk': 'Đọc/Ghi file',
        'Markdown': 'Markdown',
        'XML': 'XML',
        'CSV': 'CSV',
        'Date & Time': 'Ngày & Giờ',
        'Crypto': 'Mã hóa',
        'Compression': 'Nén file',
        'RSS Feed Read': 'Đọc RSS',
        'HTML': 'HTML',
        'Extract from File': 'Trích xuất từ file',
        'Convert to File': 'Chuyển thành file',

        // Misc UI
        'Select a trigger': 'Chọn trigger',
        'What triggers this workflow?': 'Workflow khởi động bằng gì?',
        'Add first step': 'Thêm bước đầu tiên',
        'Popular': 'Phổ biến',
        'New': 'Mới',
        'Recently used': 'Dùng gần đây',
        'Results': 'Kết quả',
        'No results found': 'Không tìm thấy',
        'Loading': 'Đang tải...',
        'Loading...': 'Đang tải...',
    };

    function translateNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent.trim();
            if (text && translations[text]) {
                node.textContent = node.textContent.replace(text, translations[text]);
            }
            return;
        }
        if (node.nodeType !== Node.ELEMENT_NODE) return;

        // Translate placeholder
        if (node.placeholder && translations[node.placeholder]) {
            node.placeholder = translations[node.placeholder];
        }
        // Translate title
        if (node.title && translations[node.title]) {
            node.title = translations[node.title];
        }

        for (const child of node.childNodes) {
            translateNode(child);
        }
    }

    function translatePage() {
        translateNode(document.body);
    }

    // Run on load and watch for dynamic content
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(translatePage, 1000));
    } else {
        setTimeout(translatePage, 1000);
    }

    // MutationObserver for dynamically loaded content
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    translateNode(node);
                }
            }
        }
    });

    function startObserver() {
        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.body) {
        startObserver();
    } else {
        document.addEventListener('DOMContentLoaded', startObserver);
    }

    // ── Auto-send test data when n8n starts listening for webhook ──
    const _origFetch = window.fetch;
    window.fetch = function(url, opts) {
        const result = _origFetch.apply(this, arguments);

        // Detect Execute workflow request
        if (opts && opts.method === 'POST' && typeof url === 'string' &&
            url.includes('/rest/workflows/') && url.includes('/run')) {

            // Extract workflow ID
            const match = url.match(/workflows\/([^/]+)\/run/);
            if (match) {
                const wfId = match[1];
                console.log('[ANSER] Execute detected for', wfId);

                // After 2s, send test data to webhook-test
                setTimeout(async () => {
                    try {
                        const r = await _origFetch(window.BASE_PATH + 'rest/workflows/' + wfId);
                        const wf = await r.json();
                        const nodes = (wf.data || wf).nodes || [];
                        let webhookPath = '';
                        for (const n of nodes) {
                            if (n.type && n.type.toLowerCase().includes('webhook')) {
                                webhookPath = (n.parameters || {}).path || '';
                                break;
                            }
                        }
                        if (!webhookPath) {
                            console.log('[ANSER] No webhook path found');
                            return;
                        }
                        console.log('[ANSER] Sending test data to', webhookPath);
                        await _origFetch('/n8n/webhook-test/' + webhookPath, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                device_id: 'ANSER-TEST',
                                event_type: 'test_from_editor',
                                amount: 100000,
                                source: 'ANSER Editor',
                                test: true,
                            }),
                        });
                        console.log('[ANSER] Test data sent!');
                    } catch (e) {
                        console.log('[ANSER] Auto-send failed:', e);
                    }
                }, 2500);
            }
        }
        return result;
    };
})();
