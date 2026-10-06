# AI_MORNING_NEWS_AGENT V1.3

Trang thông tin sống chạy trên GitHub Actions miễn phí: nguồn công khai → phân loại / pháp lý / độ mới / gộp chủ đề → HTML + snapshot + history → commit/push main → GitHub Pages. Không dùng OpenAI API hoặc dịch vụ trả phí. Không cần bật máy cá nhân.

- Website: https://matsepros-dot.github.io/AI_MORNING_NEWS_AGENT/
- Chạy tay: GitHub → Actions → Morning news V1.3 → Run workflow → main. Xem từng step và log ngay trong lần chạy.
- Lịch: `0 1 * * *` và `30 6 * * *` (08:00 và 13:30 Asia/Ho_Chi_Minh mỗi ngày). GitHub có thể khởi chạy trễ; đây là lịch cấu hình, không bảo đảm đúng từng phút.
- Windows Task Scheduler cũ được ngừng dùng cho production; `scheduler/install_task.ps1` đã deprecated và không đăng ký task mới.
- Sửa nguồn / keyword / thời gian lưu / điểm: `config/config.json`. RSS, HTML công khai và bài tham chiếu chính thống đều configurable. TVPL lỗi hoặc chặn truy cập sẽ chuyển sang nguồn Chính phủ; không vượt CAPTCHA/paywall.
- Trang chính ưu tiên latest (24 giờ), recent (72 giờ), ongoing và reference. Tin pháp lý cũ hữu ích được giữ riêng; không suy diễn ngày hiệu lực hoặc tình trạng luật. Dữ liệu ngày không chắc chắn hiển thị chưa xác định. Tin pháp lý chưa đối chiếu chính thống không xếp ưu tiên cao.
- Snapshot: `archive/YYYY-MM-DD.html`. History giữ tối đa 60 ngày theo lần nhìn thấy và 1.500 bản ghi; snapshot ngày trước được giữ. Giá USD/EUR/JPY từ Vietcombank, BTC/ETH từ CoinGecko public, kèm thời gian nguồn; nguồn lỗi giữ giá trước và đánh dấu cũ.
- Local: chạy `INSTALL.cmd` lần đầu, sau đó `RUN_AGENT.cmd --no-publish` để test. `RUN_AGENT.cmd` có thể publish thủ công bằng Git Credential Manager hiện có. Kiểm thử: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- Publish lỗi: xem Actions step commit/push; workflow chỉ retry xung đột trong checkout tạm của runner, tải remote rồi tạo lại dữ liệu. Không force-push. Branch protection có thể chặn quyền ghi; không thêm PAT. Local cần tích hợp remote trước khi publish.
- Pages giữ cấu hình main/root. Đã xác minh thực tế Pages build commit do workflow tạo và website khớp HTML cloud. Workflow chỉ cấp contents:write; không thêm PAT hoặc quyền Pages. Khi publish lỗi, so commit của lần build Pages với main để phát hiện trang chưa cập nhật.

Pipeline: exit 0 = PASS; 2 = PARTIAL; 1 = FAIL. Toàn bộ nguồn lỗi thì giữ nguyên website/history/archive. Không có tin mới vẫn dùng tin còn giá trị. No changes là thành công. Báo cáo local ở `data/run_report.json`, log xoay vòng ở `logs/agent.log`; các file này không publish. File key/.env/runtime local bị ignore và publisher dùng allowlist.

Giao diện dựa tone đỏ #EE0027, trắng/xám của slide mẫu, dùng Arial/Segoe UI. SVG tự tạo, thumbnail feed lazy load và fallback icon; không nhúng logo hoặc font proprietary. Mô tả ngắn từ nguồn, không viết tư vấn mua/bán hoặc kết luận pháp lý.

V1.3: thêm Home ở thanh đầu trang và nút nổi Về đầu trang, dùng liên kết anchor không cần JavaScript.

V1.3: header sticky, menu mobile mở/đóng, chọn nhóm tin hiện tại, nút Lên đầu cố định và card không ảnh gọn. CSS/JS có query version để tránh cache bản cũ.

Website hiển thị lịch 08:00 và 13:30 cùng thời gian tạo bản tin gần nhất theo giờ Việt Nam. Thời gian hiển thị là lúc render sau khi lấy nguồn; có thể khác lịch dự kiến do GitHub chạy trễ hoặc chạy tay. Trang đang mở cần tải lại để thấy bản mới.
