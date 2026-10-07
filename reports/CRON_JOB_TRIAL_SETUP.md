# Thử cron-job.org — chuẩn bị xong, chưa kích hoạt

Kết quả PARTIAL. 45 kiểm thử PASS. Chưa có phiên cron-job.org hoặc token chuyên dụng nên chưa test end-to-end qua dịch vụ.

Workflow `.github/workflows/external-news.yml` nhận workflow_dispatch có inputs source=cron-job.org, requested_at Unix timestamp. Config scheduler_provider=github giữ workflow mới ở standby. Không thay code lấy tin. Dùng cùng concurrency group với workflow cũ. Khi chuyển scheduler_provider=cron-job.org, guard workflow cũ chặn fetch/publish; cần bỏ cron cũ khi chuyển hẳn.

## Thiết lập cụ thể

1. Đăng nhập hoặc tạo tài khoản cron-job.org; người dùng tự nhập password/OTP và chấp nhận điều khoản khi tạo tài khoản.
2. Người dùng tạo fine-grained GitHub token chuyên dụng, chỉ repository AI_MORNING_NEWS_AGENT, quyền Actions Read and write; giữ Metadata read mặc định, không cấp Contents write hoặc quyền các repo khác. Thử nghiệm dùng thời hạn ngắn (ví dụ 7 ngày). Không dùng credential GCM rộng quyền để gửi sang dịch vụ khác.
3. Chỉ sau khi người dùng đồng ý lưu token chuyên dụng tại cron-job.org, nhập trực tiếp token vào header Authorization: Bearer ... trên cron-job.org; không đưa vào chat/file/Git/log. Token có quyền thao tác Actions trong repo, không chỉ dispatch; giới hạn repo và thời hạn để giảm phạm vi.
4. Job dùng POST tới URL trong config/cron-job-trial.template.json. Body ref=main, inputs source=cron-job.org, requested_at=%cjo:unixtime%. Các header công khai có trong template, Authorization cố ý không có. Enabled=false trước khi kiểm tra.
5. Lịch thử: timezone Asia/Ho_Chi_Minh, giờ08–17, phút0/30, ngày7 tháng10, expiration20261007173059. Không chạy lại mốc đã qua. Template đã kiểm tra trường theo tài liệu API cron-job.org.
6. Khi tài khoản/job/credential đã sẵn sàng: đổi provider, commit/push, chặn cron cũ; bật job rồi kiểm chứng mốc tương lai thật. Không lấy Test-run làm bằng chứng đúng giờ.

Guard chỉ nhận slot thống nhất, ngày hợp lệ và yêu cầu không quá15 phút sau slot; recheck trước fetch/publish. Đây là dung sai xử lý hàng đợi, không phải cam kết đúng giờ. Trial từ17:31 chặn fetch/publish. Rerun rejected. source chỉ là nhãn, không xác thực nguồn; quyền token được GitHub xác thực và job history cron-job.org cần đối chiếu để chứng minh origin. Không đảm bảo chống tất cả dispatch trùng từ tài khoản được cấp Actions write; cần đối chiếu job lịch và không bật auto-retry.

Để xác minh, cần ba bằng chứng: lịch sử cron-job (datePlanned/date/status), Actions run/summary, timestamp Pages. cron-job API success không chứng minh pipeline thành công. Bộ kiểm tra GitHub schedule cũ chỉ phản ánh provider GitHub; phải cập nhật monitor khi thực sự chuyển provider.

Nguồn: https://docs.cron-job.org/creating-cron-jobs.html ; https://docs.cron-job.org/rest-api.html ; https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
