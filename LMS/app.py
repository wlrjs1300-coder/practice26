import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from LMS.common.Session import Session
from LMS.domain import *
from LMS.service import *

app = Flask(__name__)
app.secret_key = '1234'

######################################## 회원 crud ########################################

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    uid = request.form.get('uid')
    upw = request.form.get('upw')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = 'SELECT id,name,uid,role FROM members WHERE uid = %s'
            cursor.execute(sql, (uid,))
            user = cursor.fetchone()

            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_uid'] = user['uid']
                session['user_role'] = user['role']

                return redirect(url_for('index'))
            else:
                return "<script>alert('아이디 또는 비밀번호가 틀렸습니다.');history.back();</script>"
    except Exception as e:
        print(f"로그인 오류 : {e}")
        return "로그인 중 오류가 발생했습니다. login()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return "<script>alert('로그아웃 완료!');location.href='/login';</script>"

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'GET':
        return render_template('join.html')
    uid = request.form.get('uid')
    password = request.form.get('password')
    name = request.form.get('name')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id FROM members WHERE uid = %s', (uid,))
            if cursor.fetchone():
                return "<script>alert('이미 존재하는 아이디입니다.');history.back();</script>"
            sql = 'INSERT INTO members (uid,password,name) VALUES (%s,%s,%s)'
            cursor.execute(sql, (uid, password, name))
            conn.commit()

            return "<script>alert('회원가입이 완료되었습니다.');location.href='/login'</script>"
    except Exception as e:
        print(f"회원가입 오류 : {e}")
        return "회원가입 중 오류가 발생했습니다. join()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/member/edit', methods=['GET', 'POST'])
def member_edit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute('SELECT * FROM members WHERE id = %s', (session['user_id'],))
                user_info = cursor.fetchone()
                return render_template('member_edit.html', user=user_info)
            new_name = request.form.get('name')
            new_pw = request.form.get('password')

            if new_pw:
                sql = 'UPDATE members SET name = %s, password = %s WHERE id = %s'
                cursor.execute(sql, (new_name, new_pw, session['user_id']))
            else:
                sql = 'UPDATE members SET name = %s WHERE id = %s'
                cursor.execute(sql, (new_name, session['user_id']))

            conn.commit()
            return "<script>alert('정보 수정이 완료되었습니다.');location.href='/mypage'</script>"
    except Exception as e:
        print(f"정보수정 오류 : {e}")
        return "정봇수정 중 오류가 발생했습니다. member_edit()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM members WHERE id = %s', (session['user_id'],))
            user_info = cursor.fetchone()
            cursor.execute('SELECT COUNT(*) AS board_count FROM boards WHERE member_id = %s', (session['user_id'],))
            board_count = cursor.fetchone()['board_count']

            return render_template('mypage.html', user=user_info, board_count=board_count)
    except Exception as e:
        print(f"마이페이지 오류 : {e}")
        return "마이페이지 호출 중 오류가 발생했습니다. mypage()메서드를 확인하세요."
    finally:
        conn.close()

######################################## 회원 crud ########################################

######################################## 보드 crud ########################################

@app.route('/board/write', methods=['GET', 'POST'])
def board_write():
    if request.method == 'GET':
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('board_write.html')
    elif request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        member_id = session.get('user_id')

        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = 'INSERT INTO boards (member_id,title,content) VALUES (%s,%s,%s)'
                cursor.execute(sql, (member_id, title, content))
                conn.commit()
            return redirect(url_for('board_list'))
        except Exception as e:
            print(f"게시물 작성 에러 : {e}")
            return "게시물 작성 중 오류가 발생했습니다. board_write()메서드를 확인하세요."
        finally:
            conn.close()

@app.route('/board')
def board_list():
    page = request.args.get('page', 1, type=int) # 기본 1페이지
    per_page = 10 # 한 페이지당 게시글 수
    offset = (page - 1) * per_page

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:

            # 전체 게시글 수 구하기
            cursor.execute('SELECT COUNT(*) as cnt from boards')
            total_count = cursor.fetchone()['cnt']

            # 게시글 목록 가져오기
            sql = 'SELECT b.*, m.name as writer_name FROM boards b JOIN members m ON b.member_id = m.id ORDER BY b.id DESC LIMIT %s OFFSET %s'
            cursor.execute(sql, (per_page, offset))
            rows = cursor.fetchall()

            boards = []
            for idx, row in enumerate(rows):
                board = Board.from_db(row)
                board.no = total_count - offset - idx
                boards.append(board)

            # 전체 페이지 수 계산
            total_pages = (total_count + per_page - 1) // per_page

            return render_template('board_list.html', boards=boards, page = page, total_pages=total_pages)
    finally:
        conn.close()

@app.route('/board/view/<int:board_id>')
def board_view(board_id):
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = 'SELECT b.*, m.name AS writer_name, m.uid AS writer_uid FROM boards b JOIN members m ON b.member_id = m.id WHERE b.id = %s'
            cursor.execute(sql, (board_id,))
            row = cursor.fetchone()

            if not row:
                return "<script>alert('존재하지 않는 게시글입니다.');history.back()</script>"

            board = Board.from_db(row)
            return render_template('board_view.html', board=board)
    except Exception as e:
        print(f"게시글 보기 오류 : {e}")
        return "게시글을 보는 중 오류 발생했습니다. board_view()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/board/edit/<int:board_id>', methods=['GET', 'POST'])
def board_edit(board_id):
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute('SELECT * FROM boards WHERE id = %s', (board_id,))
                row = cursor.fetchone()

                if not row:
                    return "<script>alert('존재하지 않는 게시글입니다.');history.back()</script>"

                if row.get('member_id') != session.get('user_id'):
                    return "<script>alert('수정 권한이 없습니다.');history.back()</script>"
                print(row)
                board = Board.from_db(row)
                return render_template('board_edit.html', board=board)

            elif request.method == 'POST':
                title = request.form.get('title')
                content = request.form.get('content')

                sql = 'UPDATE boards SET title = %s, content = %s WHERE id = %s'
                cursor.execute(sql, (title, content, board_id))
                conn.commit()

                return redirect(url_for('board_view', board_id=board_id))
    except Exception as e:
        print(f"게시글 수정 오류 : {e}")
        return "게시글 수정 중 오류가 발생했습니다. board_edit()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/board/delete/<int:board_id>', methods=['GET', 'POST'])
def board_delete(board_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = 'DELETE FROM boards WHERE id = %s and member_id = %s'
            cursor.execute(sql, (board_id, session.get('user_id')))
            conn.commit()

            if cursor.rowcount > 0:
                print(f"게시글 {board_id}번 삭제 성공")
                return redirect(url_for('board_list'))
            else:
                return "<script>alert('게시글을 지울 수 없습니다.');history.back()</script>"
    except Exception as e:
        print(f"게시글 삭제 오류 : {e}")
        return "게시글을 삭제 중 오류가 발생했습니다. board_delete()메서드를 확인하세요."
    finally:
        conn.close()

######################################## 보드 crud ########################################

######################################## 성적 crud ########################################

@app.route('/score/add')
def score_add():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.');history.back()</script>"

    target_uid = request.args.get('uid')
    target_name = request.args.get('name')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id FROM members WHERE uid = %s', (target_uid,))
            student = cursor.fetchone()

            existing_score = None
            if student:
                cursor.execute('SELECT * FROM scores WHERE member_id = %s', (student.get('id'),))
                row = cursor.fetchone()
                if row:
                    existing_score = Score.from_db(row)
            return render_template('score_add.html', target_uid=target_uid, target_name=target_name, existing_score=existing_score)
    finally:
        conn.close()

@app.route('/score/save', methods=['POST'])
def score_save():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.');history.back()</script>"

    target_uid = request.form.get('uid')
    kor = request.form.get('korea',0)
    eng = request.form.get('english',0)
    math = request.form.get('math',0)

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id FROM members WHERE uid = %s', (target_uid,))
            student = cursor.fetchone()

            if not student:
                return "<script>alert('존재하지 않는 학생입니다.');history.back()</script>"

            temp_score = Score(member_id=student.get('id'),kor=kor,eng=eng,math=math)

            cursor.execute('SELECT id FROM scores WHERE member_id = %s', (student.get('id'),))
            is_exist = cursor.fetchone()

            if is_exist:
                sql = 'UPDATE scores SET korean = %s, english = %s, math = %s, total = %s, average = %s, grade = %s WHERE member_id = %s'
                cursor.execute(sql,(temp_score.kor,temp_score.eng,temp_score.math,temp_score.total,temp_score.avg,temp_score.grade,student.get('id')))
            else:
                sql = 'INSERT INTO scores (member_id, korean, english, math, total, average, grade) VALUES (%s,%s,%s,%s,%s,%s,%s)'
                cursor.execute(sql,(student.get('id'),temp_score.kor,temp_score.eng,temp_score.math,temp_score.total,temp_score.avg,temp_score.grade))

                conn.commit()
                return f"<script>alert('{target_uid}학생 성적 저장 완료');location.href='/score/list';</script>"
    except Exception as e:
        print(f"성적 입력 오류 : {e}")
        conn.rollback()
    finally:
        conn.close()

@app.route('/score/list')
def score_list():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.');history.back()</script>"

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = 'SELECT m.name,m.uid,s.* FROM scores s JOIN members m ON s.member_id = m.id ORDER BY s.total DESC'
            cursor.execute(sql)
            datas = cursor.fetchall()

            score_objects = []
            for data in datas:
                s = Score.from_db(data)
                s.name = data['name']
                s.uid = data['uid']
                score_objects.append(s)

            return render_template('score_list.html', score=score_objects)
    except Exception as e:
        print(f"성적 조회 오류 : {e}")
        return "성적 조회 중 오류가 발생했습니다. score_list()메서드를 확인하세요."
    finally:
        conn.close()

@app.route('/score/members')
def score_members():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.');history.back()</script>"

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT m.id, m.uid, m.name, s.id AS score_id FROM members m LEFT JOIN scores s ON m.id = s.member_id WHERE m.role='user' ORDER BY m.name ASC"
            cursor.execute(sql)
            members = cursor.fetchall()
            return render_template('score_member_list.html', members=members)
    finally:
        conn.close()

@app.route('/score/my')
def score_my():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = 'SELECT * FROM scores WHERE member_id = %s;'
            cursor.execute(sql, (session.get('user_id'),))
            row = cursor.fetchone()
            score = Score.from_db(row) if row else None

            return render_template('score_my.html', score=score)
    finally:
        conn.close()


######################################## 성적 crud ########################################

######################################## 파일 crud ########################################

# 파일 처리용 게시판 특징
# 1. 파일 업로드 / 다운로드 가능
# 2. 단이파일 / 다중파일 업로드 처리
# 3. 서비스 패키지 활용
# 4. /upload 폴더 사용 / 용량 제한 16MB
# 5. 파일명 중복 방지용 코드 활용
# 6. db에서 부모 객체가 삭제되면 자식 객체도 삭제되게 cascade 처리

UPLOAD_FOLDER = './uploads'
# 폴더가 없으면 자동 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    # 폴더 생성용 코드 os.makedirs(이름)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 자료실 게시물 작성
@app.route('/filesboard/write', methods=['GET', 'POST'])
def filesboard_write():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        # 핵심 : getlist를 사용해야 리스트 형태로 가져옴
        files = request.files.getlist('files')

        if PostService.save_post(session['user_id'], title, content, files):
            return "<script>alert('게시글 등록이 완료되었습니다.');location.href='/filesboard';</script>"
        else:
            return "<script>alert('등록실패');history.back()</script>"
    return render_template("filesboard_write.html")

# 파일 게시판 목록
@app.route('/filesboard')
def filesboard_list():
    page = request.args.get('page',1,type=int)
    per_page = 10

    posts, total_count = PostService.get_posts(page,per_page)
    total_pages = (total_count + per_page - 1) // per_page

    return render_template('filesboard_list.html', posts=posts,page=page,total_pages=total_pages)

# 파일 게시판 게시물 내용 보기
@app.route('/filesboard/view/<int:post_id>')
def filesboard_view(post_id):
    post, titles = PostService.get_post_detail(post_id) # 두개를 리턴하면 두개로 받아야함
    if not post:
        return "<script>alert('해당 게시글이 없습니다.');location.href='/filesboard';</script>"
    return render_template('filesboard_view.html', post=post, titles=titles)

@app.route('/download/<path:filename>')
def download_file(filename):
    # 파일이 저장된 폴더(uploads)에서 파일을 찾아 전송
    # 프로트 <a href="{{ url_for('download_file', filename=file.save_name) }}" ...> 이부분 처리용
    # filename은 서버에 저장된 save_name입니다.
    # 브라우저가 다운로드 할 때 보여줄 원본 이름을 쿼리 스트링으로 받거나 DB에서 가져와야함
    origin_name = request.args.get('origin_name')
    return send_from_directory('uploads/', filename, as_attachment=True, download_name=origin_name)
    # from flask import send_from_directory 필수

    # return send_from_directory('uploads/', filename)은 브라우져에서 바로 열어버림
    # as_attachment=True 로 하면 파일 다운로드 띄움 (False의 경우 화면에 바로 띄움, 다운X)
    # 저장할 파일명은 download_name=origin_name으로 지정

@app.route('/filesboard/delete/<int:post_id>')
def filesboard_delete(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 삭제 전 작성자 확인을 위해 정보 조회
    post, _ = PostService.get_post_detail(post_id)
    # _ = 리런값을 사용하지 않겠다 라는 관례적인 표현

    if not post:
        return "<script>alert('이미 삭제된 글입니다.');location.href='/filesboard';</script>"

    # 본인 확인 (혹은 관리자 권한)
    if post['member_id'] != session.get('user_id') and session.get('user_role') != 'admin':
        return "<script>alert('삭제 권한이 없습니다.');history.back()</script>"

    if PostService.delete_post(post_id):
        return "<script>alert('성공적으로 삭제되었습니다.');location.href='/filesboard';</script>"
    else:
        return "<script>alert('삭제 중 오류가 발생했습니다.');history.back()</script>"

# 다중파일 수정용
@app.route('/filesboard/edit/<int:post_id>', methods=['GET', 'POST'])
def filesboard_edit(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        files = request.files.getlist('files')

        if PostService.update_post(post_id, title, content, files):
            return f"<script>alert('수정되었습니다.');location.href='/filesboard/view/{post_id}';</script>"
        return "<script>alert('수정실패');history.back()</script>"

    # GET 요청 시 기존 데이터 유지
    post, files = PostService.get_post_detail(post_id)
    if post.get('member_id') != session.get('user_id'):
        return "<script>alert('권한이 없습니다.');history.back()</script>"

    return render_template('filesboard_edit.html', post=post, files=files)





######################################## 파일 crud ########################################

@app.route('/')
def index():
    return render_template('main.html')
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5001, debug=True)