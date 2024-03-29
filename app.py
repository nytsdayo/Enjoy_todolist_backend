from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
# datetime モジュールのインポート
from datetime import datetime  

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo2.db'


db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.String, primary_key=True)
     # User モデルの uid に対する外部キー
    user_id = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False) 
    TodoName = db.Column(db.String(50), nullable=False)
    CreateTime = db.Column(db.String(50), nullable=False)
    ClearTime = db.Column(db.String(50), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)  # 達成状態を示す新しいフィールド
    
class User(db.Model):
    uid = db.Column(db.String, primary_key=True)
    username = db.Column(db.String(30), unique=True)
    createday = db.Column(db.String(30))
    # User と Todo のリレーションを設定
    todos = db.relationship('Todo', backref='user', lazy=True)

with app.app_context():
    db.create_all()

# Firebaseからユーザー情報を検証し、新規ユーザーの時新しくデータベースに追加する処理
@app.route('/login', methods=['GET','POST'])
@cross_origin()
def login():
    uid = request.json.get('uid')
    username = request.json.get('username')
    
    # Firebaseでの認証情報検証は省略
    
    user = User.query.filter_by(uid=uid).first()
    if user is None:
        user = User(uid=uid, username=username)
        db.session.add(user)
        db.session.commit()
    return jsonify({'message': 'Logged in successfully', 'user': {'id': uid, 'username': username}})

#ログインしたユーザーのTodoリストを返す処理
@app.route('/todos', methods=['GET'])
@cross_origin()
def get_todos():
    uid = request.args.get('uid')
    is_completed = request.args.get('is_completed', type=bool)  # 達成状態のフィルタリング用
    if is_completed is not None:
        todos = Todo.query.filter_by(user_id=uid, is_completed=is_completed).all()
    else:
        todos = Todo.query.filter_by(user_id=uid).all()
    return jsonify([{'id': todo.id, 'TodoName': todo.TodoName, 'CreateTime': todo.CreateTime, 'ClearTime': todo.ClearTime, 'isCompleted': todo.is_completed} for todo in todos])

#自分以外のユーザーの最新10件の達成リストを返す処理
@app.route('/recent_todos', methods=['GET'])
@cross_origin()
def get_recent_todos():
    uid = request.args.get('uid', type=int)  # 自分のユーザーIDを取得
    if uid:
        # 指定されたユーザー以外の達成されたTodo項目を検索し、最新10件を取得
        recent_todos = Todo.query.filter(Todo.user_id != uid, Todo.is_completed == True).order_by(Todo.ClearTime.desc()).limit(10).all()
    else:
        # ユーザーIDが指定されていない場合は、全ユーザーの達成されたTodo項目から最新10件を取得
        recent_todos = Todo.query.filter(Todo.is_completed == True).order_by(Todo.ClearTime.desc()).limit(10).all()

    return jsonify([{'id': todo.id, 'TodoName': todo.TodoName, 'CreateTime': todo.CreateTime, 'ClearTime': todo.ClearTime, 'userId': todo.user_id,'username': User.username} for todo in recent_todos])

#追加されたTodoをデータベースに入れる処理
@app.route('/add_todo', methods=['GET', 'POST'])
@cross_origin()
def add_todo():
    data = request.get_json()
    uid = data.get('uid')
    todo_name = data.get('todo')
    todo_id = data.get('todo_id')
    print("uid", uid, "todo_name", todo_name, "id", todo_id)
    create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   
    # ""でなければデータベースに追加
    if todo_name != "":
        new_todo = Todo(id=todo_id, user_id=uid, TodoName=todo_name, CreateTime=create_time, ClearTime='')
        db.session.add(new_todo)
        db.session.commit()
        print("Todo added successfully")
    else:
        print('TodoName is empty')

    # 追加後のTodoリストを取得
    user_todos = Todo.query.filter_by(user_id=uid).all()
    print(user_todos)
    
    if user_todos == []:
        return jsonify({'message': 'Nothing'})
    else:
        print(Todo.query.all())
        return jsonify([{'id': todo.id, 'TodoName': todo.TodoName, 'CreateTime': todo.CreateTime, 'ClearTime': todo.ClearTime} for todo in user_todos])

#達成ボタンが押された時クリア時間をデータベースに登録する
@app.route('/achieve_todo', methods=['PUT'])
@cross_origin()
def clear_todo():
    data = request.get_json()
    todo_id = data.get('todo_id')
    print("todo_id", todo_id)
    if not todo_id:
        return jsonify({'message': 'Todo id is required'}), 400
    todo = Todo.query.filter_by(id=todo_id).first()  # データベースからTodoオブジェクトを取得

    if todo:
        todo.is_completed = True
        todo.ClearTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.session.commit()
        print("Todo completed successfully", todo.ClearTime)
        return jsonify({'message': 'Todo completed successfully'})
    else:
        print("Todo not found")
        return jsonify({'message': 'Todo not found'}), 404
    
#自身の達成済みTodoリストをデータベースから取ってくる処理    
@app.route('/completed_todos', methods=['GET'])
@cross_origin()
def get_completed_todos():
    uid = request.args.get('uid', type=int)  # ユーザーIDをクエリパラメータから取得
    if not uid:
        return jsonify({'message': 'User ID is required'}), 400

    completed_todos = Todo.query.filter_by(user_id=uid, is_completed=True).all()
    return jsonify([{
        'id': todo.id,
        'TodoName': todo.TodoName,
        'CreateTime': todo.CreateTime,
        'ClearTime': todo.ClearTime,
        'isCompleted': todo.is_completed
    } for todo in completed_todos])

# Todoが更新されたときの処理です。
@app.route('/edit_todo/<int:todo_id>', methods=['PUT'])
@cross_origin()
def edit_todo(todo_id):
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({'message': 'Todo not found'}), 404

    data = request.json
    todo.TodoName = data.get('TodoName', todo.TodoName)
    # 他の編集可能なフィールドも同様に更新可能です。
    db.session.commit()

    # 編集後の達成されていないTodo項目を取得
    updated_todos = Todo.query.filter_by(user_id=todo.user_id, is_completed=False).all()
    return jsonify([{'id': item.id, 'TodoName': item.TodoName, 'CreateTime': item.CreateTime, 'ClearTime': item.ClearTime, 'isCompleted': item.is_completed} for item in updated_todos])

# Todoが削除されたときの処理です。
@app.route("/delete/<int:todo_id>", methods=["POST"])
@cross_origin()
def delete(todo_id):
    # URLから渡されたIDに基づいて、該当するTodoをデータベースから取得
    todo = Todo.query.filter_by(id=todo_id).first()
    # 取得したTodoをデータベースセッションから削除
    db.session.delete(todo)
    # 変更をデータベースにコミット
    db.session.commit()

# アプリを実行する処理です。
if __name__ == '__main__':
    app.run(debug=True)
