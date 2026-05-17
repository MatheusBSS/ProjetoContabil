from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os

app = Flask(__name__)
app.secret_key = 'contabilidade_marinho_2026'

base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "instance", "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    contato = db.Column(db.String(20), unique=True, nullable=False)


class Prazo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    nome_obrigacao = db.Column(db.String(200), nullable=False)
    observacao = db.Column(db.Text)
    data_vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pendente')

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
    print("✅ Banco de dados criado/atualizado com sucesso!")

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['usuario'] == 'admin' and request.form['senha'] == '123':
            session['logado'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect('/dashboard')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if not session.get('logado'):
        return redirect('/')

    hoje = date.today()
    prazos_proximos = Prazo.query.filter(Prazo.status != 'Concluído',
                                         Prazo.data_vencimento <= hoje.replace(day=hoje.day + 7)).count()
    prazos_vencidos = Prazo.query.filter(Prazo.status != 'Concluído', Prazo.data_vencimento < hoje).count()
    urgentes = Prazo.query.filter(Prazo.status == 'Pendente').order_by(Prazo.data_vencimento).limit(5).all()

    return render_template('dashboard.html',
                           total_clientes=Cliente.query.count(),
                           total_prazos=Prazo.query.count(),
                           prazos_proximos=prazos_proximos,
                           prazos_vencidos=prazos_vencidos,
                           urgentes=urgentes)

@app.route('/cadastrar', methods=['GET', 'POST'])
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
def listar_clientes():
    if not session.get('logado'):
        return redirect('/')
    clientes = Cliente.query.all()
    return render_template('index.html', clientes=clientes)


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
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
def excluir_cliente(id):
    if not session.get('logado'):
        return redirect('/')
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect('/clientes')

@app.route('/prazos', methods=['GET', 'POST'])
def prazos_listar():
    if not session.get('logado'):
        return redirect('/')

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

        novo_prazo = Prazo(
            cliente_id=int(cliente_id),
            nome_obrigacao=nome_obrigacao,
            observacao=observacao,
            data_vencimento=date.fromisoformat(data_venc)
        )
        db.session.add(novo_prazo)
        db.session.commit()
        flash('Prazo cadastrado com sucesso!', 'success')
        return redirect('/prazos')

    # Filtragem
    query = Prazo.query
    if busca:
        query = query.filter(
            (Prazo.cliente.has(Cliente.nome.ilike(f'%{busca}%'))) |
            (Prazo.nome_obrigacao.ilike(f'%{busca}%'))
        )
    if filtro == 'pendente':
        query = query.filter(Prazo.status == 'Pendente')
    elif filtro == 'concluido':
        query = query.filter(Prazo.status == 'Concluído')

    prazos = query.all()
    hoje = date.today()

    return render_template('prazos.html', prazos=prazos, clientes=Cliente.query.all(), busca=busca, filtro=filtro,
                           hoje=hoje)

@app.route('/editar_prazo/<int:id>', methods=['GET', 'POST'])
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
def marcar_concluido(id):
    if not session.get('logado'):
        return redirect('/')
    prazo = Prazo.query.get_or_404(id)
    prazo.status = 'Concluído'
    db.session.commit()
    flash('Prazo marcado como concluído!', 'success')
    return redirect('/prazos')

@app.route('/excluir_prazo/<int:id>')
def excluir_prazo(id):
    if not session.get('logado'):
        return redirect('/')
    prazo = Prazo.query.get_or_404(id)
    db.session.delete(prazo)
    db.session.commit()
    flash('Prazo excluído com sucesso!', 'success')
    return redirect('/prazos')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)