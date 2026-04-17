from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = '123'

clientes = []

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

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['usuario']
        senha = request.form['senha']

        if user == 'admin' and senha == '123':
            session['logado'] = True
            return redirect('/dashboard')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logado'):
        return redirect('/')
    return render_template('dashboard.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        contato = request.form['contato']

        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        # VALIDAR CPF
        if not validar_cpf(cpf_limpo):
            return "CPF inválido!"

        # VERIFICAR DUPLICADOS
        for c in clientes:
            if c['cpf'] == cpf_limpo:
                return "CPF já cadastrado!"
            if c['contato'] == contato:
                return "Telefone já cadastrado!"

        clientes.append({
            'nome': nome,
            'cpf': cpf_limpo,
            'contato': contato
        })

        return redirect('/clientes')

    return render_template('cadastrar.html')

@app.route('/clientes')
def listar():
    return render_template('index.html', clientes=clientes)

@app.route('/excluir/<int:id>')
def excluir(id):
    clientes.pop(id)
    return redirect('/clientes')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        contato = request.form['contato']

        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        if not validar_cpf(cpf_limpo):
            return "CPF inválido!"

        for i, c in enumerate(clientes):
            if i != id:
                if c['cpf'] == cpf_limpo:
                    return "CPF já cadastrado!"
                if c['contato'] == contato:
                    return "Telefone já cadastrado!"

        clientes[id] = {
            'nome': nome,
            'cpf': cpf_limpo,
            'contato': contato
        }

        return redirect('/clientes')

    return render_template('editar.html', cliente=clientes[id], id=id)

app.run(debug=True)
