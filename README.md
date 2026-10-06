# AI_MORNING_NEWS_AGENT V1

Bản tin sáng miễn phí từ RSS công khai. Không dùng OpenAI API, không tạo tóm tắt bằng AI. Python 3.10+ và Git có Git Credential Manager là đủ.

1. **Cài lần đầu:** double-click `INSTALL.cmd`. Cài dependency vào `.venv`.
2. **Chạy manual:** double-click `RUN_AGENT.cmd`. Chạy từ thư mục khác cũng được. `RUN_AGENT.cmd --no-publish` chỉ tạo bản tin tại máy.
3. **Website:** https://matsepros-dot.github.io/AI_MORNING_NEWS_AGENT/ hoặc mở `index.html`. Kho ngày cũ nằm trong `archive/`.
4. **Log:** `logs/agent.log` (xoay vòng), lỗi launcher trong `logs/launcher.log`. Thống kê lần chạy trong `data/run_report.json`.
5. **Sửa nguồn/keyword:** `config/config.json`. Nguồn RSS/Atom dùng `name`, `url`, `priority`, `category`, `enabled`; nguồn không ổn định được bỏ qua và ghi log. Có thể chỉnh thời gian lọc, số tin, trọng số, ngưỡng loại trùng và retention history.
6. **Scheduler:** chạy PowerShell `-ExecutionPolicy Bypass -File scheduler\install_task.ps1` để tạo/cập nhật task `AI_MORNING_NEWS_AGENT_0700`. Xem bằng Task Scheduler hoặc `Get-ScheduledTask -TaskName AI_MORNING_NEWS_AGENT_0700`. Chạy 07:00 giờ Windows, bù lịch khi có thể, tối đa 20 phút, không chạy song song. Task dùng tài khoản hiện tại khi đã đăng nhập; máy cần có mạng và phiên Windows đã đăng nhập để dùng Git Credential Manager. Nếu sửa giờ trong config, chạy lại script đăng ký.
7. **Publish lỗi:** dữ liệu đã tạo vẫn được giữ. Nếu chưa có phiên đăng nhập Git, double-click `CONNECT_GITHUB.cmd`, hoàn tất luồng Git Credential Manager trên GitHub; script tự chạy bản tin và publish sau khi đăng nhập. Phiên Chrome đơn thuần chưa đủ để Git push; cần hoàn tất luồng xác thực GCM. Không lưu password/token vào source. Installer ghi đường dẫn Git đang dùng vào `config/runtime.json` (không commit), để Task Scheduler không phụ thuộc PATH của Codex. Nếu Git đổi vị trí, chạy lại `INSTALL.cmd`. Không tự force-push hay ghi đè thay đổi remote; nếu remote đã thay đổi cần kiểm tra và tích hợp trước.
8. **Chạy lại cùng ngày:** chạy `RUN_AGENT.cmd` lần nữa; cập nhật cùng file ngày, không nhân bản history. URL các ngày trước bị hạn chế lặp; URL mới vẫn được xét. History giữ 45 ngày; archive vẫn giữ bản tin cũ.

Exit code: `0` PASS; `2` PARTIAL (ít hơn số tin tối thiểu, publish lỗi hoặc đang chạy); `1` FAIL. Nếu toàn bộ nguồn lỗi/không có tin mới, giữ nguyên website, archive và history. Những bài thiếu ngày được dùng giờ thu thập và giảm điểm; hiển thị rõ chưa có ngày nguồn. Description chỉ là đoạn RSS tối đa 320 ký tự. Tiêu đề gần giống nhưng khác số không bị tự gộp.

Kiểm thử: `.venv\Scripts\python.exe -m unittest discover -s tests -v`. Các lỗi mạng, nguồn và publish được mô phỏng bằng mock; manual run dùng RSS thật. Không đọc hoặc đưa file key trên máy lên Git. Publisher dùng danh sách đường dẫn cho phép thay vì `git add .`.
