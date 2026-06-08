from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

from extensions import db
from models import User, Document


from models import User
app = Flask(__name__)
app.secret_key = "secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyshare.db'

# Khởi tạo db với app
db.init_app(app)

# Tạo thư mục upload nếu chưa có
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@app.route('/') # trang chủ, hiển thị danh sách tài liệu và cho phép tìm kiếm
def index():
    query = request.args.get('q')# tìm kiếm bằng tiêu đề
    if query:# nếu có hiển thị kết quả
        docs = Document.query.filter(Document.title.contains(query)).all()
    else:# nếu không hiển thị tất cả
        docs = Document.query.all()

    current_user = None # mặc định là chưa đăng nhập
    if 'user_id' in session: # nếu đã đăng nhập thì lấy thông tin user để hiển thị
        current_user = User.query.get(session['user_id'])

    return render_template('index.html', docs=docs, current_user=current_user)# truyền docs và current_user vào template để hiển thị


@app.route('/register', methods=['GET','POST']) #trang đăng ,dùng cả 2 phương thức
def register():
    if request.method == 'POST': # nếu là POST thì xử lý form đăng ký
        username = request.form['username'] #lấy username từ form đăng ký
        existing_user = User.query.filter_by(username=username).first()# kiểm tra xem username đã tồn tại chưa
        if existing_user:# nếu đã tồn tại thì hiển thị lỗi
            return render_template('register.html', error="Tên đăng nhập đã tồn tại!")

        password = generate_password_hash(request.form['password'])# mã hóa mật khẩu trước khi lưu vào database
        
        # Nếu muốn tạo admin, gán role="admin"
        user = User(username=username, password=password, role="user")# tạo user mới với role mặc định là "user"
        
        db.session.add(user)# thêm user vào session của db
        db.session.commit()# commit để lưu vào database
        session['user_id'] = user.id# lưu user_id vào session để tự động đăng nhập sau khi đăng ký thành công
        return redirect(url_for('index'))# đăg kí thành công thì chuyển vô trang chủ
    return render_template('register.html')# ngược lại là GET thì hiển thị form đăg kí




@app.route('/login', methods=['GET','POST']) #trang đăng nhập
def login():
    if request.method == 'POST':# xử lí khi là POST
        user = User.query.filter_by(username=request.form['username']).first()# tìm trong db xem có tên đăng nhập không
        if user and check_password_hash(user.password, request.form['password']):# nếu có và mật khẩu đúng thì vô
            session['user_id'] = user.id # lưu user_id vào session để đánh dấu đã đăng nhập
            return redirect(url_for('index')) # đăg nhập được thì chuyển vô trag chủ
    return render_template('login.html')

@app.route('/logout') #trang đăg xuất
def logout(): 
    session.pop('user_id', None)# xóa user_id khỏi session để đăng xuất
    return redirect(url_for('index')) # xong thì chuyển về trang chủ

@app.route('/upload', methods=['GET','POST']) # trag up tài liệu
def upload():
    if 'user_id' not in session: # chưa đăg nhập thì ko upload đc
        return redirect(url_for('login')) # chuyển đến trag đăg nhập
    if request.method == 'POST': # nếu là POST thì xử lý form upload
        title = request.form['title'] # tiêu đề tài liệu
        description = request.form['description'] # mô tả tài liệu
        file = request.files['file'] # file tài liệu được chọn để upload
        filename = file.filename # tên file gốc của tài liệu
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename) # đường dẫn để lưu file trên server
        file.save(filepath) # lưu file vào đường dẫn đã định nghĩa

        doc = Document(title=title, description=description, 
                       file_url=filepath, user_id=session['user_id']) #tạo bảng tài liệu với các thông tin của tài liệu,và user_id để biết là của ai
        db.session.add(doc) # thêm tài liệu mới vào session của db
        db.session.commit() # commit để lưu
        return redirect(url_for('index')) # up xg thì chuyển về trang chủ
    return render_template('upload.html') # ngược lại là GET thì hiển thị form upload




@app.route('/delete/<int:id>') # trang xóa tài liệu
def delete(id):
    if 'user_id' not in session: # nếu chưa đăng nhập thì không được xóa
        return redirect(url_for('login')) # chuyển đến trang đăng nhập
    doc = Document.query.get_or_404(id) # tìm tài liệu theo id, nếu không tìm thấy thì trả về lỗi 404
    user = User.query.get(session['user_id']) # lấy thông tin user hiện tại từ db để kiểm tra quyền xóa
    if user and (user.role == "admin" or doc.user_id == user.id):#nếu chuẩn là người up tài liệu hoặc là admin thì được xóa
        db.session.delete(doc) # xóa tài liệu khỏi session của db
        db.session.commit() # lưu thay đổi
    # Kiểm tra lại user trong session
    if not User.query.get(session['user_id']):# 
        session.pop('user_id', None)# nếu user đã bị xóa, thì đăng xuất luok
        return redirect(url_for('login')) # chuyển đến trang đăng nhập
    return redirect(url_for('admin'))  # xóa xong thì chuyển về trang admin để xem danh sách tài liệu còn lại



@app.route('/delete_user/<int:id>') #xóa người dùng
def delete_user(id):
    if 'user_id' not in session: # nếu chưa đăng nhập thì không được xóa
        return redirect(url_for('login'))
    current = User.query.get(session['user_id']) # lấy thông tin user hiện tại từ db để kiểm tra quyền xóa
    if current.role != "admin": # nếu không phải admin thì không được xóa
        return "Bạn không có quyền!"

    user = User.query.get_or_404(id) # tìm user theo id, nếu không tìm thấy thì trả về lỗi 404

    # Không cho admin tự xóa chính mình
    if user.id == current.id:
        return "Không thể tự xóa tài khoản admin của bạn!"

    # Xóa tất cả tài liệu của user trước
    Document.query.filter_by(user_id=user.id).delete()

    # Xóa user
    db.session.delete(user)
    db.session.commit()

    # Sau khi xóa user khác, admin vẫn giữ nguyên session
    return redirect(url_for('admin')) # sau khi xóa thì vẫn ở lại trag admin để tiếp tục quản lý


@app.route('/admin')   # trang admin để quản lý người dùng và tài liệu
def admin():
    if 'user_id' not in session: # nếu chưa đăng nhập thì không được vào trang admin
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role != "admin":
        return "Bạn không có quyền truy cập!" # ko phải admin thì ko đc vào trang admin

    users = User.query.all() # lấy tất cả người dùng để hiển thị trong trang admin
    docs = Document.query.all() # lấy tất cả tài liệu để hiển thị trong trang admin, admin có thể xóa bất kỳ tài liệu nào
    return render_template('admin.html', users=users, docs=docs, current_user=user)# truyền users, docs và current_user vào template để hiển thị





@app.route('/reset_password/<int:id>', methods=['GET','POST']) # trang reset mk cho user
def reset_password(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    current = User.query.get(session['user_id'])
    if current.role != "admin":
        return "Bạn không có quyền!"  # như trên

    user = User.query.get_or_404(id)# tìm user theo id, nếu không tìm thấy thì trả về lỗi 404

    if request.method == 'POST': # nếu là POST thì xử lý form reset mật khẩu
        new_password = request.form['new_password'] # lấy mật khẩu mới từ form
        user.password = generate_password_hash(new_password) # mã hóa mật khẩu mới trước khi lưu vào database
        db.session.commit()
        return redirect(url_for('admin')) # reset xong thì chuyển về trang admin để tiếp tục quản lý

    return render_template('reset_password.html', user=user) 



with app.app_context(): # tạo bảng trong db
    db.create_all()

    # Tạo admin mặc định nếu chưa có
  # Tạo bảng và admin mặc định


    admin_username = "admin" # 
    admin_password = "123456" # tên và mk của admin
    existing_admin = User.query.filter_by(username=admin_username).first() # kiểm tra xem admin đã tồn tại chưa
    if not existing_admin:# nếu chưa tồn tại thì tạo admin mới
        admin = User( # tạo admin mới ngay tại đây luok
            username=admin_username,
            password=generate_password_hash(admin_password),
            role="admin"
        )# tạo user admin với role là "admin"
        db.session.add(admin)# lưu vào db
        db.session.commit()
        print("Admin mặc định đã được tạo:", admin_username, "/", admin_password)


if __name__ == '__main__':
    app.run(debug=True)
