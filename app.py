import streamlit as st
import pandas as pd
import gspread
import random
import smtplib
from email.mime.text import MIMEText
import re
import json
import requests

# ==========================================
# CONFIGURAÇÃO DO ADMINISTRADOR (ATENÇÃO AQUI)
# ==========================================
# Digite o seu CPF (com o zero inicial, apenas os números) entre as aspas abaixo:
CPF_DO_ADMINISTRADOR = "06698038474" 

st.set_page_config(page_title="Busca de Fornecedores", page_icon="🏢", layout="wide")

# ==========================================
# 1. CONEXÃO COM A PLANILHA DO GOOGLE
# ==========================================
@st.cache_resource(ttl=600)
def conectar_planilha():
    try:
        credenciais_json = json.loads(st.secrets["google_credentials"])
        gc = gspread.service_account_from_dict(credenciais_json)
        planilha = gc.open_by_url(st.secrets["link_planilha"])
        return planilha
    except Exception as e:
        st.error("Erro na conexão com o banco de dados. Verifique os Secrets.")
        st.stop()

planilha = conectar_planilha()
aba_usuarios = planilha.worksheet("Usuarios")
aba_fornecedores = planilha.worksheet("Fornecedores")

# ==========================================
# 2. FUNÇÕES DE APOIO
# ==========================================
def validar_senha(senha):
    if len(senha) < 8: return False
    if not re.search(r"[a-z]", senha): return False
    if not re.search(r"[A-Z]", senha): return False
    if not re.search(r"[0-9]", senha): return False
    return True

def limpar_cpf(cpf):
    cpf_str = str(cpf).replace('.0', '')
    cpf_num = re.sub(r'[^0-9]', '', cpf_str)
    return cpf_num.zfill(11)

def formatar_cpf_visual(cpf):
    c = limpar_cpf(cpf)
    if len(c) == 11:
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    return c

def buscar_cep(cep):
    cep_limpo = re.sub(r'[^0-9]', '', str(cep))
    if len(cep_limpo) == 8:
        try:
            res = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=10)
            if res.status_code == 200:
                return res.json()
        except: pass
    return {}

def enviar_email(destinatario, codigo):
    remetente = "SEU_EMAIL_AQUI@gmail.com" 
    senha_app = "SUA_SENHA_DE_APP_AQUI" 
    msg = MIMEText(f"Seu código de verificação é: {codigo}")
    msg['Subject'] = 'Código de Verificação - Plataforma'
    msg['From'] = remetente
    msg['To'] = destinatario
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remetente, senha_app)
        server.sendmail(remetente, [destinatario], msg.as_string())
        server.quit()
    except:
        st.warning(f"AVISO: E-mail não configurado. Código simulado para teste: {codigo}")

# ==========================================
# 3. INTERFACE DE LOGIN E CADASTRO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['cpf_atual'] = ""

if 'menu_login' not in st.session_state:
    st.session_state['menu_login'] = "Entrar"

if not st.session_state['logado']:
    st.title("🏢 Plataforma de Fornecedores")
    
    menu = st.radio("Selecione uma opção:", ["Entrar", "Cadastrar Novo Usuário"], key="menu_login", horizontal=True)
    
    if menu == "Entrar":
        st.subheader("Acesse sua conta")
        login_cpf = st.text_input("CPF")
        login_senha = st.text_input("Senha", type="password")
        
        if st.button("Fazer Login"):
            dados_users = aba_usuarios.get_all_records()
            df_users = pd.DataFrame(dados_users)
            
            if not df_users.empty:
                df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                cpf_digitado_tratado = limpar_cpf(login_cpf)
                
                if cpf_digitado_tratado in df_users['cpf_tratado'].tolist():
                    usuario_encontrado = df_users[df_users['cpf_tratado'] == cpf_digitado_tratado].iloc[0]
                    
                    if str(usuario_encontrado['senha']) == login_senha:
                        if int(usuario_encontrado['verificado']) == 1:
                            st.session_state['logado'] = True
                            st.session_state['cpf_atual'] = cpf_digitado_tratado
                            st.rerun()
                        else:
                            st.session_state['validando_email'] = cpf_digitado_tratado
                            st.warning("Primeiro acesso detectado! Verifique seu e-mail.")
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("CPF não encontrado.")
            else:
                st.error("Nenhum usuário cadastrado.")

        if 'validando_email' in st.session_state:
            codigo_digitado = st.text_input("Digite o código de 6 dígitos:")
            if st.button("Validar Código"):
                dados_users = aba_usuarios.get_all_records()
                for i, row in enumerate(dados_users):
                    if limpar_cpf(row['cpf']) == st.session_state['validando_email']:
                        if str(row['codigo_verificacao']) == codigo_digitado:
                            aba_usuarios.update_cell(i + 2, 13, 1) 
                            st.success("Verificado com sucesso! Faça login novamente.")
                            del st.session_state['validando_email']
                            break
                        else:
                            st.error("Código incorreto.")

    elif menu == "Cadastrar Novo Usuário":
        st.subheader("Cadastro")
        
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Completo *")
        cpf_cadastro = col2.text_input("CPF *")
        email = col1.text_input("E-mail *")
        
        st.write("### Endereço")
        cep = st.text_input("CEP * (Digite apenas os números e clique fora da caixa)")
        
        rua_val, bairro_val, cidade_val = "", "", ""
        if cep and len(re.sub(r'[^0-9]', '', cep)) == 8:
            dados_cep = buscar_cep(cep)
            if dados_cep and "erro" not in dados_cep:
                rua_val = dados_cep.get("logradouro", "")
                bairro_val = dados_cep.get("bairro", "")
                cidade_val = f"{dados_cep.get('localidade', '')} - {dados_cep.get('uf', '')}"
                st.success("CEP encontrado!")
            elif dados_cep:
                st.error("CEP não localizado.")

        col3, col4 = st.columns([3, 1])
        rua = col3.text_input("Rua *", value=rua_val)
        numero = col4.text_input("Número *")
        
        col5, col6 = st.columns([2, 2])
        bairro = col5.text_input("Bairro *", value=bairro_val)
        cidade = col6.text_input("Cidade *", value=cidade_val)
        
        st.write("### Informações Profissionais")
        perfil = st.selectbox("Qual o seu perfil? *", [
            "1 - Síndico Orgânico", "2 - Síndico Profissional", "3 - Gerente de Condomínio",
            "4 - Funcionário de Condomínio", "5 - Morador de um condomínio", 
            "6 - Sem vinculação"
        ])
        
        condominios = ""
        if perfil != "6 - Sem vinculação":
            condominios = st.text_area("Nome do(s) condomínio(s) (Obrigatório para seu perfil):")
        
        senha = st.text_input("Crie uma Senha * (Mín. 8 char, 1 Maiúscula, 1 Minúscula, 1 Número)", type="password")
        termo = st.checkbox("Declaro me responsabilizar pelas informações cadastradas (Minhas e de Terceiros). *")
        
        if st.button("Concluir Cadastro"):
            df_users = pd.DataFrame(aba_usuarios.get_all_records())
            
            if not df_users.empty:
                df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                cpfs_cadastrados = df_users['cpf_tratado'].tolist()
            else:
                cpfs_cadastrados = []
                
            cpf_limpo_cadastro = limpar_cpf(cpf_cadastro)
            cpf_para_salvar = formatar_cpf_visual(cpf_limpo_cadastro)

            if not nome or not cpf_cadastro or not email or not cep or not rua or not numero or not bairro or not cidade:
                st.error("Preencha todos os campos obrigatórios (*), incluindo o CEP.")
            elif cpf_limpo_cadastro in cpfs_cadastrados:
                st.error("Este CPF já está cadastrado.")
            elif perfil != "6 - Sem vinculação" and not condominios:
                st.error("Preencha o nome do condomínio.")
            elif not validar_senha(senha):
                st.error("A senha deve ter no mínimo 8 caracteres, contendo letra maiúscula, minúscula e número.")
            elif not termo:
                st.error("Você precisa aceitar os termos de responsabilidade.")
            else:
                codigo = str(random.randint(100000, 999999))
                aba_usuarios.append_row([
                    cpf_para_salvar, nome, email, cep, rua, numero, bairro, cidade, 
                    perfil, condominios, senha, codigo, 0
                ])
                enviar_email(email, codigo)
                st.session_state['sucesso_cadastro'] = True
                
        if st.session_state.get('sucesso_cadastro'):
            st.success("✅ Cadastro realizado com sucesso! O código de 6 dígitos foi enviado ao seu e-mail para o primeiro acesso.")
            if st.button("Ir para a Tela de Acesso (Login)"):
                st.session_state['sucesso_cadastro'] = False
                st.session_state['menu_login'] = "Entrar"
                st.rerun()

# ==========================================
# 4. PLATAFORMA PRINCIPAL (Após Login)
# ==========================================
else:
    st.title("🔍 Busca de Prestadores e Fornecedores")
    st.info("⚠️ A plataforma é uma ferramenta de busca. Não nos responsabilizamos pelos serviços contratados.")
    st.success("✅ Profissionais validados pela COMUNIDADE SÍNDICOS DA PARAÍBA.")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['cpf_atual'] = ""
        st.rerun()

    opcoes_menu = ["Buscar", "Adicionar Novo"]
    if st.session_state.get('cpf_atual') == limpar_cpf(CPF_DO_ADMINISTRADOR):
        opcoes_menu.append("Administrar Prioridades")

    menu_interno = st.radio("Menu Principal", opcoes_menu, horizontal=True)

    if menu_interno == "Buscar":
        termo = st.text_input("Buscar por Nome ou Ramo de Atuação:")
        if st.button("Pesquisar"):
            df_forn = pd.DataFrame(aba_fornecedores.get_all_records())
            if not df_forn.empty:
                df_forn = df_forn.fillna("")
                df_forn['Todos_Ramos'] = df_forn['RAMO 1'].astype(str) + " " + df_forn['RAMO 2'].astype(str) + " " + df_forn['RAMO 3'].astype(str) + " " + df_forn['RAMO 4'].astype(str) + " " + df_forn['RAMO 5'].astype(str)
                
                filtro = df_forn[
                    df_forn['NOME'].astype(str).str.contains(termo, case=False, na=False) | 
                    df_forn['Todos_Ramos'].str.contains(termo, case=False, na=False)
                ]
                
                if 'PRIORIDADE' not in filtro.columns:
                    filtro['PRIORIDADE'] = 0
                else:
                    filtro['PRIORIDADE'] = pd.to_numeric(filtro['PRIORIDADE'], errors='coerce').fillna(0)
                
                filtro = filtro.sort_values(by=['PRIORIDADE', 'NOME'], ascending=[False, True])
                
                for _, row in filtro.iterrows():
                    ramos_lista = []
                    for i in range(1, 6):
                        col_ramo = f"RAMO {i}"
                        if col_ramo in row and str(row[col_ramo]).strip() != "":
                            ramos_lista.append(str(row[col_ramo]).strip())
                    
                    contatos_lista = []
                    if 'CONTATO 1' in row and str(row['CONTATO 1']).strip() != "":
                        contatos_lista.append(str(row['CONTATO 1']).strip())
                    if 'CONTATO 2' in row and str(row['CONTATO 2']).strip() != "":
                        contatos_lista.append(str(row['CONTATO 2']).strip())
                    
                    st.markdown(f"### 🏢 {row.get('NOME', 'Sem Nome')}")
                    st.markdown(f"**Ramos de Atuação:** {', '.join(ramos_lista)}")
                    st.markdown(f"**Contatos:** {' / '.join(contatos_lista)}")
                    if 'EMAIL' in row and str(row['EMAIL']).strip() != "":
                        st.markdown(f"**E-mail:** {row['EMAIL']}")
                    st.divider()
            else:
                st.warning("Nenhum fornecedor cadastrado na base de dados.")

    elif menu_interno == "Adicionar Novo":
        st.write("Insira os dados do novo profissional. Se ele tiver apenas um ramo ou contato, deixe os outros em branco.")
        with st.form("form_f"):
            nome_f = st.text_input("Nome *")
            col_t1, col_t2 = st.columns(2)
            tel1_f = col_t1.text_input("Contato 1 *")
            tel2_f = col_t2.text_input("Contato 2")
            email_f = st.text_input("E-mail")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            ramo1_f = col_r1.text_input("Ramo 1 *")
            ramo2_f = col_r2.text_input("Ramo 2")
            ramo3_f = col_r3.text_input("Ramo 3")
            
            col_r4, col_r5 = st.columns(2)
            ramo4_f = col_r4.text_input("Ramo 4")
            ramo5_f = col_r5.text_input("Ramo 5")

            if st.form_submit_button("Cadastrar na Planilha"):
                if not nome_f or not ramo1_f or not tel1_f:
                    st.error("Nome, Ramo 1 e Contato 1 são obrigatórios.")
                else:
                    aba_fornecedores.append_row([
                        nome_f, tel1_f, tel2_f, email_f, 
                        ramo1_f, ramo2_f, ramo3_f, ramo4_f, ramo5_f, 0
                    ])
                    st.success("Fornecedor cadastrado com sucesso direto na sua planilha!")

    elif menu_interno == "Administrar Prioridades":
        st.write("Coloque o valor '1' para destacar a empresa no topo, e '0' para posição normal.")
        df_forn = pd.DataFrame(aba_fornecedores.get_all_records())
        if not df_forn.empty:
            col_nomes = aba_fornecedores.row_values(1)
            try:
                indice_coluna_prio = col_nomes.index("PRIORIDADE") + 1
            except ValueError:
                indice_coluna_prio = 10 
                
            for i, row in df_forn.iterrows():
                col1, col2 = st.columns([3,1])
                nome_display = str(row.get('NOME', 'Sem nome'))
                ramo_display = str(row.get('RAMO 1', 'Sem ramo'))
                
                col1.write(f"**{nome_display}** (Ramo principal: {ramo_display})")
                
                valor_atual = 0
                if 'PRIORIDADE' in row and str(row['PRIORIDADE']).strip().isdigit():
                    valor_atual = int(row['PRIORIDADE'])
                
                nova_prio = col2.selectbox("Prioridade", [0, 1], index=[0, 1].index(valor_atual), key=f"prio_{i}")
                
                if nova_prio != valor_atual:
                    aba_fornecedores.update_cell(i + 2, indice_coluna_prio, nova_prio)
                    st.success(f"Prioridade de {nome_display} alterada!")
                    st.rerun()
