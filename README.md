Note: Thay đổi 23/10/2025
- proxy.py: ở hàm run_proxy, khi proxy chạy, nó sẽ listen 50 client là nhiều nhất, khi đó, proxy sẽ có ip và port của nó, khi có client, nó sẽ có luôn conn và adrr của client. Dòng 202 thêm vào hàm handle_client để xử lý khi có client đến. Lưu ý: Chưa hiểu ý cách tạo "Multi-thread" ở đây cho lắm vì thầy dùng "while True" chạy tuần tự.
- back_end.py: Ta có từ proxy -> proxy.handle_client -> proxy.forward_request -> backend có port là 9000. Khi backend listen bắt được request được forward từ trên proxy xuống, nó tiến hành gọi cho backend chạy, và do mỗi proxy sẽ điều hướng tới 1 backend trong backend pool tương ứng, ta cũng phải handle_client những request truyền từ trên proxy xuống (Dòng 93).
- respone.py:
  + Hai elif dòng 318 và 320: Original code chưa hỗ trợ xử lý ảnh và icon nên ghi thêm.
  + Đoạn sub_if dòng 104: Do là cái original code của thầy nó chưa xử lý việc xử lý ảnh và icon nên phải thêm vào. Cụ thể, nếu là image/ thì sẽ có thể là image/png (welcome.png) hoặc x-icon nếu favicon.ico.
  + Đoạn 209-216: Đoạn đó là mới thêm vào, vì file ví dụ như index.html khi mình open thì open theo dạng "r" tức là đọc file bình thường rồi f.read(). Do là dạng file text bình thường, ta phải chuyển thành byte bằng cách encode, rồi gán nó với header rồi mới respone cho client được. Nhưng nếu trường hợp là ảnh hoặc icon thì ta buộc phải đọc theo byte nên phải phân ra thêm "rb", và đã là byte rồi thì không cần encode.
  + Đoạn 206-214: Hàm build_response_header(...) là đang xử lý định dạng header theo HTTP để sau đó send back vể client. Theo HTTP, định dạng chuẩn sẽ là:'|KEY| + ":" + " "+ |VALUE| + "/r/n"', và bắt đầu của header sẽ là "HTTP/1.1 200 OK\r\n" (Do là thành công, còn trường hợp failed thì thầy đã xử lý bằng 404). Cuối header bắt buộc phải là "/r/n". Sau đó là encode header đó, và header này sẽ nằm trước Đoạn 209-216


Note: Thay đổi 26/10/2025 (Vấn đề về Login và Cookie)
- Mình thêm vào một file test.html, tức là ban đầu đề bài nói là khi quay lại trang / method GET, nếu như không có cookie thì trả về lỗi 401. Mình đọc thấy nó cấn cấn, kiểu nó khó hình dung nên làm cách khác một chút: Là ban đầu tới trang chủ, bấm vào nút Login để Login, Login thất bại thì trả về lỗi 401, còn nếu ban dầu không Login mà vô thẳng Test, nó sẽ kiểm tra có Cookie chưa, mà Cookie muốn có là phải xác thực.
- Overall: Hiện tại code của mình đã có thể làm thao tác đăng nhập, và cookie. Mình cố tình thiết kế nó khác Task 1B một chút, thay vì là qua vì / với method GET thì mình cho nó quay lên /test method GET để test cookie, còn phần đăng nhập thì tạo nút trong index.html, bấm vào nút đó dẫn đến login.html, điền thông tin và bấm "Login" thì tự động gửi đến /login method POST.
- index.html: Thêm một href để dẫn đến file login.html
- request.py:
  + Build một hàm mới là hàm extract_and_validate_username_password(), tức là cái username với cái password, nó sẽ được return trong cái body message HTTP nó gửi về từ login/html, thông qua /login method POST.         Thì với cái body message đó mình có thể trích xuất header, cookie, phiên bản của HTTP,.... Hàm này build mới, để mà extract ra username và password trong cái đống đó thôi, nếu username == "Duong" và password       == "14112005" thì sẽ set cho self.auth (một thuộc tính boolean) là True (thuộc tính này dùng tiếp bên Respone).
  +  Ở dòng 86: Thêm vào việc phân tìm domain /test thành /test.html.
- respone.py:
  + Mình build một hàm mới là build_unauthorized(), để deal với lỗi 401 Unauthorized (Content-Length set thành 16 thôi).
  + Ở dòng 253: Tuân theo protocol về header của HTTP, domain Set-Cookie, có nghĩa là Server sẽ set cookie của client, và chúng ta chỉ làm điều này nếu request.auth == True (Tức là nếu đã xác thực).
  + Ở trong hàm build_respone(), mình thêm vào phân xác thực:
    1. Nếu domain hiện tại là /login, mà trước đó bên Request là xác thực thất bại (request.auth == False) thì trả về lỗi 401.
    2. Nếu domain hiện tại là /test (/test.html), mà không tìm thấy cookie, thì trả về lỗi 401.

