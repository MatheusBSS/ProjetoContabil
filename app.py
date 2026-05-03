from flask import Flask, render_template, request, redirect, session, flash
from datetime import date

app = Flask(__name__)
app.secret_key = 'contmarinho'

clientes = []
prazos = []

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
    prazos_proximos = len([p for p in prazos if p['status'] != 'Concluído' and (p['data_vencimento'] - hoje).days <= 7])
    prazos_vencidos = len([p for p in prazos if p['status'] != 'Concluído' and (p['data_vencimento'] - hoje).days < 0])

    urgentes = sorted([p for p in prazos if p['status'] == 'Pendente'], key=lambda p: p['data_vencimento'])[:5]

    return render_template('dashboard.html',
                           total_clientes=len(clientes),
                           total_prazos=len(prazos),
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

        for c in clientes:
            if c['cpf'] == cpf_limpo or c['contato'] == contato:
                flash('CPF ou telefone já cadastrado!', 'error')
                return redirect('/cadastrar')

        clientes.append({'nome': nome, 'cpf': cpf_limpo, 'contato': contato})
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect('/clientes')
    return render_template('cadastrar.html')


@app.route('/clientes')
def listar_clientes():
    if not session.get('logado'):
        return redirect('/')
    return render_template('index.html', clientes=clientes)


@app.route('/excluir/<int:id>')
def excluir_cliente(id):
    if not session.get('logado'):
        return redirect('/')
    if 0 <= id < len(clientes):
        clientes.pop(id)
        flash('Cliente excluído com sucesso!', 'success')
    return redirect('/clientes')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if not session.get('logado'):
        return redirect('/')
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

        for i, c in enumerate(clientes):
            if i != id and (c['cpf'] == cpf_limpo or c['contato'] == contato):
                flash('CPF ou telefone já cadastrado!', 'error')
                return redirect('/clientes')

        clientes[id] = {'nome': nome, 'cpf': cpf_limpo, 'contato': contato}
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect('/clientes')
    return render_template('editar.html', cliente=clientes[id], id=id)

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

        cliente_id = int(cliente_id)
        data_vencimento = date.fromisoformat(data_venc)
        cliente_nome = next((c['nome'] for c in clientes if int(c['cpf']) == cliente_id), "Cliente não encontrado")

        prazos.append({
            'id': len(prazos),
            'cliente_id': cliente_id,
            'cliente_nome': cliente_nome,
            'nome_obrigacao': nome_obrigacao,
            'observacao': observacao,
            'data_vencimento': data_vencimento,
            'status': 'Pendente'
        })
        flash('Prazo cadastrado com sucesso!', 'success')
        return redirect('/prazos')

    prazos_filtrados = prazos
    if busca:
        prazos_filtrados = [p for p in prazos_filtrados if
                            busca in p['cliente_nome'].lower() or busca in p['nome_obrigacao'].lower()]
    if filtro == 'pendente':
        prazos_filtrados = [p for p in prazos_filtrados if p['status'] == 'Pendente']
    elif filtro == 'concluido':
        prazos_filtrados = [p for p in prazos_filtrados if p['status'] == 'Concluído']

    hoje = date.today()

    return render_template('prazos.html',
                           prazos=prazos_filtrados,
                           clientes=clientes,
                           busca=busca,
                           filtro=filtro,
                           hoje=hoje)


@app.route('/editar_prazo/<int:id>', methods=['GET', 'POST'])
def editar_prazo(id):
    if not session.get('logado'):
        return redirect('/')
    if request.method == 'POST':
        prazos[id]['nome_obrigacao'] = request.form['nome_obrigacao']
        prazos[id]['observacao'] = request.form.get('observacao', '')
        prazos[id]['data_vencimento'] = date.fromisoformat(request.form['data_vencimento'])
        flash('Prazo atualizado com sucesso!', 'success')
        return redirect('/prazos')
    return render_template('editar_prazo.html', prazo=prazos[id], id=id)


@app.route('/marcar_concluido/<int:id>')
def marcar_concluido(id):
    if not session.get('logado'):
        return redirect('/')
    if 0 <= id < len(prazos):
        prazos[id]['status'] = 'Concluído'
        flash('Prazo marcado como concluído!', 'success')
    return redirect('/prazos')


@app.route('/excluir_prazo/<int:id>')
def excluir_prazo(id):
    if not session.get('logado'):
        return redirect('/')
    if 0 <= id < len(prazos):
        prazos.pop(id)
        flash('Prazo excluído com sucesso!', 'success')
    return redirect('/prazos')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)