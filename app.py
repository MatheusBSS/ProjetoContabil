from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'contabilidade_marinho_2026'

base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "instance", "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    contato = db.Column(db.String(20), unique=True, nullable=False)

class Prazo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    nome_obrigacao = db.Column(db.String(200), nullable=False)
    observacao = db.Column(db.Text)
    data_vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pendente')
    usuario = db.relationship('Usuario', backref='prazos_criados')
    cliente = db.relationship('Cliente', backref='prazos')

def formatar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10
    return dig1 == int(cpf[9]) and dig2 == int(cpf[10])

app.jinja_env.globals.update(formatar_cpf=formatar_cpf)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_senha(senha):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect('/dashboard')
        else:
            flash('Email ou senha incorretos.', 'error')
            return redirect('/login')
    return render_template('login.html')

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        if not nome or not email or not senha:
            flash('Todos os campos são obrigatórios!', 'error')
            return redirect('/registrar')
        if Usuario.query.filter_by(email=email).first():
            flash('Este email já está cadastrado.', 'error')
            return redirect('/registrar')
        novo_usuario = Usuario(nome=nome, email=email)
        novo_usuario.set_senha(senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect('/login')
    return render_template('registrar.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect('/')

@app.route('/dashboard')
@login_required
def dashboard():
    hoje = date.today()
    data_limite = hoje + timedelta(days=7)

    prazos_proximos = Prazo.query.filter(
        Prazo.status != 'Concluído',
        Prazo.data_vencimento <= data_limite
    ).count()

    prazos_vencidos = Prazo.query.filter(
        Prazo.status != 'Concluído',
        Prazo.data_vencimento < hoje
    ).count()

    urgentes = Prazo.query.filter(Prazo.status == 'Pendente').order_by(Prazo.data_vencimento).limit(5).all()

    return render_template('dashboard.html',
                           total_clientes=Cliente.query.count(),
                           total_prazos=Prazo.query.count(),
                           prazos_proximos=prazos_proximos,
                           prazos_vencidos=prazos_vencidos,
                           urgentes=urgentes,
                           usuario=current_user)

@app.route('/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        contato = request.form.get('contato', '').strip()
        if not nome or not cpf or not contato:
            flash('Todos os campos são obrigatórios!', 'error')
            return redirect('/cadastrar')
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        if not validar_cpf(cpf_limpo):
            flash('CPF inválido!', 'error')
            return redirect('/cadastrar')
        if Cliente.query.filter_by(cpf=cpf_limpo).first() or Cliente.query.filter_by(contato=contato).first():
            flash('CPF ou telefone já cadastrado!', 'error')
            return redirect('/cadastrar')
        novo = Cliente(nome=nome, cpf=cpf_limpo, contato=contato)
        db.session.add(novo)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect('/clientes')
    return render_template('cadastrar.html')

@app.route('/clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('index.html', clientes=clientes)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        contato = request.form.get('contato', '').strip()
        if not nome or not cpf or not contato:
            flash('Todos os campos são obrigatórios!', 'error')
            return redirect('/clientes')
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        if not validar_cpf(cpf_limpo):
            flash('CPF inválido!', 'error')
            return redirect('/clientes')
        if Cliente.query.filter(Cliente.id != id, (Cliente.cpf == cpf_limpo) | (Cliente.contato == contato)).first():
            flash('CPF ou telefone já cadastrado!', 'error')
            return redirect('/clientes')
        cliente.nome = nome
        cliente.cpf = cpf_limpo
        cliente.contato = contato
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect('/clientes')
    return render_template('editar.html', cliente=cliente)

@app.route('/excluir/<int:id>')
@login_required
def excluir_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect('/clientes')

@app.route('/prazos', methods=['GET', 'POST'])
@login_required
def prazos_listar():
    busca = request.args.get('busca', '').lower()
    filtro = request.args.get('filtro', 'todos')
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        nome_obrigacao = request.form.get('nome_obrigacao', '').strip()
        observacao = request.form.get('observacao', '').strip()
        data_venc = request.form.get('data_vencimento')
        if not cliente_id or not nome_obrigacao or not data_venc:
            flash('Todos os campos são obrigatórios!', 'error')
            return redirect('/prazos')
        novo = Prazo(usuario_id=current_user.id, cliente_id=int(cliente_id), nome_obrigacao=nome_obrigacao, observacao=observacao, data_vencimento=date.fromisoformat(data_venc))
        db.session.add(novo)
        db.session.commit()
        flash('Prazo cadastrado com sucesso!', 'success')
        return redirect('/prazos')
    query = Prazo.query.filter_by(usuario_id=current_user.id)
    if busca:
        query = query.filter((Prazo.cliente.has(Cliente.nome.ilike(f'%{busca}%'))) | (Prazo.nome_obrigacao.ilike(f'%{busca}%')))
    if filtro == 'pendente':
        query = query.filter(Prazo.status == 'Pendente')
    elif filtro == 'concluido':
        query = query.filter(Prazo.status == 'Concluído')
    prazos = query.all()
    hoje = date.today()
    return render_template('prazos.html', prazos=prazos, clientes=Cliente.query.all(), busca=busca, filtro=filtro, hoje=hoje)

@app.route('/editar_prazo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_prazo(id):
    prazo = Prazo.query.get_or_404(id)
    if request.method == 'POST':
        prazo.nome_obrigacao = request.form['nome_obrigacao']
        prazo.observacao = request.form.get('observacao', '')
        prazo.data_vencimento = date.fromisoformat(request.form['data_vencimento'])
        db.session.commit()
        flash('Prazo atualizado com sucesso!', 'success')
        return redirect('/prazos')
    return render_template('editar_prazo.html', prazo=prazo)

@app.route('/marcar_concluido/<int:id>')
@login_required
def marcar_concluido(id):
    prazo = Prazo.query.get_or_404(id)
    prazo.status = 'Concluído'
    db.session.commit()
    flash('Prazo marcado como concluído!', 'success')
    return redirect('/prazos')

@app.route('/excluir_prazo/<int:id>')
@login_required
def excluir_prazo(id):
    prazo = Prazo.query.get_or_404(id)
    db.session.delete(prazo)
    db.session.commit()
    flash('Prazo excluído com sucesso!', 'success')
    return redirect('/prazos')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)