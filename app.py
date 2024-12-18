from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Configuração do banco de dados e upload
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "produtos.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

from werkzeug.utils import secure_filename


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cria o diretório de upload, se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicializa o banco de dados
def criar_tabelas():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            descricao TEXT,
            preco REAL,
            imagem TEXT
        )
    ''')
    conexao.commit()
    conexao.close()

# Rota inicial
# @app.route('/')
# def index():
#     return render_template('index.html')

# Rota para visualizar produtos
@app.route('/visualizar')
def visualizar():
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM produtos")
    produtos = cursor.fetchall()
    conexao.close()
    return render_template('visualizar.html', produtos=produtos)

# Rota para cadastrar produtos
@app.route('/cadastrar', methods=["GET", "POST"])
def cadastrar():
    if request.method == "POST":
        codigo = request.form['codigo']
        descricao = request.form['descricao']
        preco = request.form['preco']
        imagem_file = request.files['imagem']

        # Define o caminho padrão para a imagem "sem_imagem.png"
        if imagem_file and imagem_file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(imagem_file.filename)
            imagem_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem_file.save(imagem_path)
            imagem_url = f'static/uploads/{filename}'
        else:
            imagem_url = 'static/uploads/sem_imagem.png'  # Caminho para a imagem padrão


        try:
            conexao = sqlite3.connect(DB_PATH)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO produtos (codigo, descricao, preco, imagem) VALUES (?, ?, ?, ?)",
                           (codigo, descricao, preco, imagem_url))
            conexao.commit()
            conexao.close()
            flash("Produto cadastrado com sucesso!", "success")
        except sqlite3.IntegrityError:
            flash("Código já existe!", "danger")
        return redirect(url_for('visualizar'))
    return render_template('cadastrar.html')

# Rota para excluir produtos
@app.route('/excluir/<int:produto_id>')
def excluir(produto_id):
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    conexao.commit()
    conexao.close()
    flash("Produto excluído com sucesso!", "success")
    return redirect(url_for('visualizar'))

@app.route('/editar/<codigo>', methods=['GET', 'POST'])
def editar_produto(codigo):
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()

    if request.method == 'POST':
        descricao = request.form['descricao']
        preco = request.form['preco']
        imagem_file = request.files['imagem']

        # Recupera a imagem atual do banco
        cursor.execute("SELECT imagem FROM produtos WHERE codigo = ?", (str(codigo),))
        imagem_atual = cursor.fetchone()[0]

        # Processa a nova imagem
        if imagem_file and imagem_file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(imagem_file.filename)
            imagem_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem_file.save(imagem_path)
            imagem_path_db = f'static/uploads/{filename}'
        else:
            imagem_path_db = imagem_atual  # Mantém a imagem anterior

        # Atualiza os dados no banco de dados
        cursor.execute("""
            UPDATE produtos
            SET descricao = ?, preco = ?, imagem = ?
            WHERE codigo = ?
        """, (descricao, preco, imagem_path_db, str(codigo)))
        conexao.commit()
        conexao.close()

        flash("Produto atualizado com sucesso!", "success")
        return redirect(url_for('visualizar'))

    # Busca os dados do produto para preencher o formulário
    cursor.execute("SELECT codigo, descricao, preco, imagem FROM produtos WHERE codigo = ?", (str(codigo),))
    produto = cursor.fetchone()
    conexao.close()

    if not produto:
        flash("Produto não encontrado!", "danger")
        return redirect(url_for('visualizar'))

    return render_template('editar.html', produto=produto)



@app.route('/buscar', methods=["GET", "POST"])
def buscar():
    resultado = None
    if request.method == "POST":
        codigo = request.form.get("codigo")
        descricao = request.form.get("descricao")
        conexao = sqlite3.connect(DB_PATH)
        cursor = conexao.cursor()
        if codigo:
            cursor.execute("SELECT * FROM produtos WHERE codigo = ?", (codigo,))
        elif descricao:
            cursor.execute("SELECT * FROM produtos WHERE descricao LIKE ?", (f"%{descricao}%",))
        resultado = cursor.fetchall()
        conexao.close()
    return render_template('buscar.html', resultado=resultado)

@app.route('/buscar-sugestao')
def buscar_sugestao():
    query = request.args.get('query', '').lower()
    sugestoes = []
    if query:
        conexao = sqlite3.connect(DB_PATH)
        cursor = conexao.cursor()
        cursor.execute("SELECT DISTINCT descricao FROM produtos WHERE LOWER(descricao) LIKE ?", (f"%{query}%",))
        sugestoes = [row[0] for row in cursor.fetchall()]
        conexao.close()
    return jsonify(sugestoes=sugestoes)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Captura o código de barras do produto
        codigo = request.form.get('codigo')
        conexao = sqlite3.connect(DB_PATH)
        cursor = conexao.cursor()

        # Busca o produto pelo código
        cursor.execute("SELECT codigo, descricao, preco FROM produtos WHERE codigo = ?", (str(codigo),))
        produto = cursor.fetchone()
        conexao.close()

        # Se o produto for encontrado
        if produto:
            flash("Produto adicionado à lista!", "success")
            return render_template('index.html', produto=produto)
        else:
            flash("Produto não encontrado!", "danger")
    return render_template('index.html', produto=None)


@app.route('/buscar-produto')
def buscar_produto():
    codigo = request.args.get('codigo')
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()

    cursor.execute("SELECT codigo, descricao, preco, imagem FROM produtos WHERE codigo = ?", (str(codigo),))
    produto = cursor.fetchone()
    conexao.close()

    if produto:
        # Ajusta o caminho da imagem removendo 'static/'
        imagem_path = produto[3].replace("static/", "") if produto[3] else "uploads/sem_imagem.png"
        return jsonify({
            "sucesso": True,
            "produto": {
                "codigo": produto[0],
                "descricao": produto[1],
                "preco": float(str(produto[2]).replace(',', '.')),  # Garante que o preço esteja no formato correto
                "imagem": url_for('static', filename=imagem_path)
            }
        })
    else:
        return jsonify({"sucesso": False})





if __name__ == "__main__":
    criar_tabelas()
    app.run(debug=True)
