import streamlit as st
import pandas as pd
import gspread
import random
import smtplib
from email.mime.text import MIMEText
import re
import json
import requests
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DO ADMINISTRADOR (ATENÇÃO AQUI)
# ==========================================
# Digite o seu CPF (com o zero inicial, apenas os números) entre as aspas abaixo:
CPF_DO_ADMINISTRADOR = "06698038474" 

st.set_page_config(page_title="Comunidade Síndicos da Paraíba", page_icon="🏢", layout="wide")

# ==========================================
# APLICAÇÃO DE ESTILOS VISUAIS (CSS)
# ==========================================
estilo_customizado = """
    <style>
    /* Estilização dos textos e cabeçalhos */
    h1, h2, h3 { color: #1E3A8A !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Personalização dos botões */
    .stButton > button { border-radius: 8px !important; font-weight: 600 !important; transition: all 0.3s ease !important; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2) !important; }
    
    /* Ocultar elementos desnecessários */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

# ==========================================
# 1. CONEXÃO COM A PLANILHA DO GOOGLE E SEGREDOS
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
aba_sugestoes = planilha.worksheet("Sugestoes") 
aba_logs = planilha.worksheet("Logs") # Nova aba de estatísticas conectada!

# ==========================================
# 2. FUNÇÕES DE APOIO E TELEMETRIA
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

def enviar_email(destinatario, codigo, tipo="cadastro"):
    try:
        remetente = st.secrets["email_remetente"]
        senha_app = st.secrets["senha_email"]
        
        assunto = 'Código de Acesso - Plataforma' if tipo == "cadastro" else 'Recuperação de Senha - Plataforma'
        msg = MIMEText(f"Seu código de verificação é: {codigo}")
        msg['Subject'] = assunto
        msg['From'] = remetente
        msg['To'] = destinatario
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remetente, senha_app)
        server.sendmail(remetente, [destinatario], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error("Falha ao enviar e-mail. Verifique os Secrets.")
        return False

def ir_para_login():
    st.session_state['sucesso_cadastro'] = False
    st.session_state['menu_login'] = "Entrar"

# FUNÇÃO INVISÍVEL QUE GRAVA AS AÇÕES DO USUÁRIO NA PLANILHA DE LOGS
def registrar_log(cpf, acao, termo_nome="", termo_ramo="", fornecedores=""):
    try:
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        aba_logs.append_row([data_atual, str(cpf), acao, termo_nome, termo_ramo, fornecedores])
    except Exception as e:
        pass # Ignora erro silenciosamente para não atrapalhar a navegação do usuário

# ==========================================
# 3. INTERFACE DE LOGIN, CADASTRO E RECUPERAÇÃO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['cpf_atual'] = ""

if 'menu_login' not in st.session_state:
    st.session_state['menu_login'] = "Entrar"

if not st.session_state['logado']:
    
    st.markdown(
        """
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&h=300&q=80" 
                 style="width: 100%; max-height: 220px; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        </div>
        """, unsafe_allow_html=True
    )
    
    st.markdown("<h1 style='text-align: center; margin-bottom: 20px; font-size: 34px;'>PORTAL DA COMUNIDADE SÍNDICOS DA PARAÍBA</h1>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="background-color: #FFFFFF; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 30px; border-left: 5px solid #1E3A8A; color: #334155; font-size: 15px; line-height: 1.6;">
            <p style="margin-top: 0; font-size: 16px;">Bem-vindo ao portal oficial vinculado à <strong>Comunidade Síndicos da Paraíba</strong>. Nossa plataforma foi desenvolvida para facilitar a busca por profissionais qualificados, atendendo com excelência tanto às demandas estruturais de <strong>condomínios</strong> quanto às necessidades particulares dos <strong>condôminos</strong>.</p>
            <p style="margin-bottom: 10px; color: #1E3A8A;"><strong>Nossos pilares de segurança e qualidade:</strong></p>
            <ul style="margin-bottom: 0;">
                <li style="margin-bottom: 8px;"><strong>Validação Real:</strong> Todos os prestadores de serviços e fornecedores cadastrados nesta base possuem uma origem em comum: foram expressamente indicados em nosso grupo oficial de WhatsApp. Isso significa que cada profissional listado já foi contratado, testado e atendeu plenamente às expectativas do cliente (síndico, morador ou membro do grupo).</li>
                <li><strong>Curadoria de Indicações:</strong> Qualquer usuário externo pode utilizar o portal para sugerir novos fornecedores. No entanto, para preservar a integridade da nossa rede, o cadastro só será aprovado e efetivado se o profissional possuir validação e histórico de satisfação comprovado dentro da nossa Comunidade.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True
    )
    
    menu = st.radio("Navegação:", ["Entrar", "Cadastrar Novo Usuário", "Esqueci minha senha"], key="menu_login", horizontal=True)
    st.write("---")

    if menu == "Entrar":
        col_espaco1, col_form, col_espaco2 = st.columns([1, 2, 1])
        with col_form:
            st.subheader("Acesse sua conta")
            login_cpf = st.text_input("CPF")
            login_senha = st.text_input("Senha", type="password")
            
            if st.button("Fazer Login", use_container_width=True):
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
                                registrar_log(cpf_digitado_tratado, "Acesso") # Registra o Login
                                st.rerun()
                            else:
                                st.session_state['validando_email'] = cpf_digitado_tratado
                                st.warning("Primeiro acesso detectado! Verifique seu e-mail para inserir o código.")
                        else:
                            st.error("Senha incorreta.")
                    else:
                        st.error("CPF não encontrado.")
                else:
                    st.error("Nenhum usuário cadastrado.")

            if 'validando_email' in st.session_state:
                st.info("✉️ Enviamos um código para o seu e-mail cadastrado.")
                codigo_digitado = st.text_input("Digite o código de 6 dígitos:")
                if st.button("Validar Código", use_container_width=True):
                    dados_users = aba_usuarios.get_all_records()
                    for i, row in enumerate(dados_users):
                        if limpar_cpf(row['cpf']) == st.session_state['validando_email']:
                            if str(row['codigo_verificacao']) == codigo_digitado:
                                aba_usuarios.update_cell(i + 2, 14, 1) 
                                st.session_state['logado'] = True
                                st.session_state['cpf_atual'] = st.session_state['validando_email']
                                registrar_log(st.session_state['validando_email'], "Acesso") # Registra o Login
                                del st.session_state['validando_email']
                                st.rerun()
                                break
                            else:
                                st.error("Código incorreto.")

    elif menu == "Cadastrar Novo Usuário":
        st.subheader("Cadastro de Usuário")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome Completo *")
            cpf_cadastro = col2.text_input("CPF *")
            
            col_email, col_tel = st.columns(2)
            email = col_email.text_input("E-mail *")
            telefone_cadastro = col_tel.text_input("Contato Telefônico *")
            
            st.markdown("#### 📍 Endereço")
            cep = st.text_input("CEP * (Apenas números, clique fora após digitar)")
            
            rua_val, bairro_val, cidade_val = "", "", ""
            if cep and len(re.sub(r'[^0-9]', '', cep)) == 8:
                dados_cep = buscar_cep(cep)
                if dados_cep and "erro" not in dados_cep:
                    rua_val = dados_cep.get("logradouro", "")
                    bairro_val = dados_cep.get("bairro", "")
                    cidade_val = f"{dados_cep.get('localidade', '')} - {dados_cep.get('uf', '')}"
                    st.success("✅ CEP localizado!")
                elif dados_cep:
                    st.error("CEP não localizado.")

            col3, col4 = st.columns([3, 1])
            rua = col3.text_input("Rua *", value=rua_val)
            numero = col4.text_input("Número *")
            
            col5, col6 = st.columns([2, 2])
            bairro = col5.text_input("Bairro *", value=bairro_val)
            cidade = col6.text_input("Cidade *", value=cidade_val)
            
            st.markdown("#### 💼 Informações Profissionais")
            perfil = st.selectbox("Qual o seu perfil? *", [
                "1 - Síndico Orgânico", "2 - Síndico Profissional", "3 - Gerente de Condomínio",
                "4 - Funcionário de Condomínio", "5 - Morador de um condomínio", 
                "6 - Sem vinculação"
            ])
            
            condominios = ""
            if perfil != "6 - Sem vinculação":
                condominios = st.text_area("Nome do(s) condomínio(s) (Obrigatório para seu perfil):")
            
            st.markdown("#### 🔒 Segurança")
            senha = st.text_input("Crie uma Senha * (Mín. 8 char, 1 Maiúscula, 1 Minúscula, 1 Número)", type="password")
            termo = st.checkbox("Declaro me responsabilizar pelas informações cadastradas (Minhas e de Terceiros). *")
            
            if st.button("Concluir Cadastro", type="primary"):
                df_users = pd.DataFrame(aba_usuarios.get_all_records())
                
                if not df_users.empty:
                    df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                    cpfs_cadastrados = df_users['cpf_tratado'].tolist()
                else:
                    cpfs_cadastrados = []
                    
                cpf_limpo_cadastro = limpar_cpf(cpf_cadastro)
                cpf_para_salvar = formatar_cpf_visual(cpf_limpo_cadastro)

                if not nome or not cpf_cadastro or not email or not telefone_cadastro or not cep or not rua or not numero or not bairro or not cidade:
                    st.error("Preencha todos os campos obrigatórios (*).")
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
                    sucesso_email = enviar_email(email, codigo, "cadastro")
                    
                    if sucesso_email:
                        aba_usuarios.append_row([
                            cpf_para_salvar, nome, email, telefone_cadastro, cep, rua, numero, bairro, cidade, 
                            perfil, condominios, senha, codigo, 0
                        ])
                        st.session_state['sucesso_cadastro'] = True
                    
        if st.session_state.get('sucesso_cadastro'):
            st.success("✅ Cadastro realizado com sucesso! O código de 6 dígitos foi enviado ao seu e-mail.")
            st.button("Ir para a Tela de Acesso (Login)", on_click=ir_para_login)

    elif menu == "Esqueci minha senha":
        col_espaco1, col_form, col_espaco2 = st.columns([1, 2, 1])
        with col_form:
            st.subheader("Recuperação de Senha")
            
            if 'fase_recuperacao' not in st.session_state:
                st.session_state['fase_recuperacao'] = 1
                st.session_state['cpf_recuperacao'] = ""
                
            if st.session_state['fase_recuperacao'] == 1:
                st.markdown("<p style='color: #64748B;'>Informe seu CPF para receber o código no e-mail cadastrado.</p>", unsafe_allow_html=True)
                cpf_rec = st.text_input("CPF Cadastrado:")
                if st.button("Enviar Código", use_container_width=True):
                    cpf_limpo_rec = limpar_cpf(cpf_rec)
                    df_users = pd.DataFrame(aba_usuarios.get_all_records())
                    if not df_users.empty:
                        df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                        if cpf_limpo_rec in df_users['cpf_tratado'].tolist():
                            usuario = df_users[df_users['cpf_tratado'] == cpf_limpo_rec].iloc[0]
                            email_usuario = usuario['email']
                            
                            codigo_rec = str(random.randint(100000, 999999))
                            indice_planilha = df_users[df_users['cpf_tratado'] == cpf_limpo_rec].index[0]
                            aba_usuarios.update_cell(int(indice_planilha) + 2, 13, codigo_rec)
                            
                            if enviar_email(email_usuario, codigo_rec, "recuperacao"):
                                st.session_state['fase_recuperacao'] = 2
                                st.session_state['cpf_recuperacao'] = cpf_limpo_rec
                                st.rerun()
                        else:
                            st.error("CPF não encontrado.")
                    else:
                        st.error("Base de dados vazia.")
                        
            elif st.session_state['fase_recuperacao'] == 2:
                st.info("✉️ Código enviado. Verifique também o Lixo Eletrônico/Spam.")
                codigo_digitado_rec = st.text_input("Digite o código de 6 dígitos:")
                if st.button("Validar Código", use_container_width=True):
                    df_users = pd.DataFrame(aba_usuarios.get_all_records())
                    df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                    usuario = df_users[df_users['cpf_tratado'] == st.session_state['cpf_recuperacao']].iloc[0]
                    
                    if str(usuario['codigo_verificacao']) == str(codigo_digitado_rec):
                        st.session_state['fase_recuperacao'] = 3
                        st.rerun()
                    else:
                        st.error("Código incorreto.")
                        
            elif st.session_state['fase_recuperacao'] == 3:
                st.success("✅ Código validado!")
                nova_senha = st.text_input("Nova Senha * (Mín. 8 char, 1 Maiúscula, 1 Minúscula, 1 Número)", type="password")
                if st.button("Salvar Nova Senha", type="primary", use_container_width=True):
                    if validar_senha(nova_senha):
                        df_users = pd.DataFrame(aba_usuarios.get_all_records())
                        df_users['cpf_tratado'] = df_users['cpf'].apply(limpar_cpf)
                        indice_planilha = df_users[df_users['cpf_tratado'] == st.session_state['cpf_recuperacao']].index[0]
                        
                        aba_usuarios.update_cell(int(indice_planilha) + 2, 12, nova_senha)
                        st.success("Senha atualizada! Redirecionando...")
                        
                        st.session_state['fase_recuperacao'] = 1
                        st.session_state['cpf_recuperacao'] = ""
                        st.button("Entrar no Sistema", on_click=ir_para_login)
                    else:
                        st.error("A senha não atende aos requisitos.")

# ==========================================
# 4. PLATAFORMA PRINCIPAL (Após Login)
# ==========================================
else:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&h=200&q=80" 
                 style="width: 100%; max-height: 120px; object-fit: cover; border-radius: 10px;">
        </div>
        """, unsafe_allow_html=True
    )
    
    st.markdown("<h2 style='color: #1E3A8A; margin-top: -10px;'>PORTAL DA COMUNIDADE SÍNDICOS DA PARAÍBA</h2>", unsafe_allow_html=True)
    st.info("✅ Todos os profissionais abaixo possuem histórico de satisfação atestado na Comunidade.")
    
    if st.sidebar.button("🚪 Sair / Logout"):
        st.session_state['logado'] = False
        st.session_state['cpf_atual'] = ""
        st.rerun()

    opcoes_menu = ["Buscar", "Sugerir Contato de Prestador/Fornecedor"]
    
    if st.session_state.get('cpf_atual') == limpar_cpf(CPF_DO_ADMINISTRADOR):
        opcoes_menu.append("Cadastrar Fornecedor Direto")
        opcoes_menu.append("Aprovar Sugestões")
        opcoes_menu.append("Administrar Prioridades")
        opcoes_menu.append("Estatísticas e Relatórios") # NOVO MENU INSERIDO

    menu_interno = st.radio("Menu de Acesso Rápido:", opcoes_menu, horizontal=True)
    st.write("---")

    if menu_interno == "Buscar":
        with st.container(border=True):
            st.markdown("#### Filtros de Pesquisa")
            col_b1, col_b2 = st.columns(2)
            busca_nome = col_b1.text_input("👤 Nome do Fornecedor/Empresa:")
            busca_ramo = col_b2.text_input("🛠️ Ramo de Atuação (Ex: Elevador, Hidráulica):")
            btn_pesquisar = st.button("🔍 Pesquisar", type="primary")
        
        if btn_pesquisar:
            df_forn = pd.DataFrame(aba_fornecedores.get_all_records())
            if not df_forn.empty:
                df_forn = df_forn.fillna("")
                df_forn['Todos_Ramos'] = df_forn['RAMO 1'].astype(str) + " " + df_forn['RAMO 2'].astype(str) + " " + df_forn['RAMO 3'].astype(str) + " " + df_forn['RAMO 4'].astype(str) + " " + df_forn['RAMO 5'].astype(str)
                
                filtro = df_forn.copy()
                
                if busca_nome.strip() != "":
                    filtro = filtro[filtro['NOME'].astype(str).str.contains(busca_nome.strip(), case=False, na=False)]
                
                if busca_ramo.strip() != "":
                    filtro = filtro[filtro['Todos_Ramos'].str.contains(busca_ramo.strip(), case=False, na=False)]
                
                if 'PRIORIDADE' not in filtro.columns:
                    filtro['PRIORIDADE'] = 0
                else:
                    filtro['PRIORIDADE'] = pd.to_numeric(filtro['PRIORIDADE'], errors='coerce').fillna(0)
                
                filtro = filtro.sort_values(by=['PRIORIDADE', 'NOME'], ascending=[False, True])
                
                if filtro.empty:
                    st.warning("Nenhum fornecedor encontrado com estes termos.")
                else:
                    st.markdown(f"**{len(filtro)} resultado(s) encontrado(s):**")
                    
                    # REGISTRA O LOG DA BUSCA
                    nomes_encontrados = ", ".join(filtro['NOME'].astype(str).tolist())
                    registrar_log(st.session_state['cpf_atual'], "Busca", busca_nome.strip(), busca_ramo.strip(), nomes_encontrados)
                    
                    for _, row in filtro.iterrows():
                        ramos_lista = [str(row[f"RAMO {i}"]).strip() for i in range(1, 6) if str(row.get(f"RAMO {i}", "")).strip() != ""]
                        
                        contatos_lista = []
                        if 'CONTATO 1' in row and str(row['CONTATO 1']).strip() != "":
                            contatos_lista.append(str(row['CONTATO 1']).strip())
                        if 'CONTATO 2' in row and str(row['CONTATO 2']).strip() != "":
                            contatos_lista.append(str(row['CONTATO 2']).strip())
                            
                        email_texto = f"\n✉️ E-mail: {row['EMAIL']}" if 'EMAIL' in row and str(row['EMAIL']).strip() != "" else ""
                        
                        with st.container(border=True):
                            st.markdown("👇 **COPIAR INFORMAÇÕES:** Passe o mouse dentro da caixa abaixo e clique no ícone de copiar 📋 que aparecerá no canto superior direito.")
                            texto_copia = f"🏢 EMPRESA: {row.get('NOME', 'Sem Nome')}\n🛠️ RAMOS DE ATUAÇÃO: {', '.join(ramos_lista)}\n📞 CONTATOS: {' / '.join(contatos_lista)}{email_texto}"
                            st.code(texto_copia, language="text")
            else:
                st.warning("A base de dados está vazia.")

    # ==============================================================
    # NOVO MENU: ESTATÍSTICAS E RELATÓRIOS (EXCLUSIVO ADMINISTRADOR)
    # ==============================================================
    elif menu_interno == "Estatísticas e Relatórios":
        st.subheader("📊 Relatórios e Estatísticas de Uso")
        st.write("Analise o comportamento dos usuários e as demandas mais populares.")
        
        # Filtros de Data
        col_d1, col_d2 = st.columns(2)
        data_inicial = col_d1.date_input("Data Inicial", value=pd.to_datetime("today") - pd.Timedelta(days=30))
        data_final = col_d2.date_input("Data Final", value=pd.to_datetime("today"))
        
        if st.button("Gerar Relatório", type="primary"):
            df_logs = pd.DataFrame(aba_logs.get_all_records())
            
            if df_logs.empty:
                st.warning("Nenhum dado de acesso ou busca registrado ainda.")
            else:
                # Converte as datas do log para poder filtrar
                df_logs['Data'] = pd.to_datetime(df_logs['Data'], errors='coerce').dt.date
                
                # Filtra pelo período escolhido
                mask = (df_logs['Data'] >= data_inicial) & (df_logs['Data'] <= data_final)
                df_filtrado = df_logs.loc[mask]
                
                if df_filtrado.empty:
                    st.info("Nenhuma atividade registrada no período selecionado.")
                else:
                    st.write("---")
                    st.markdown("### 👥 Engajamento de Usuários")
                    
                    # Separa quem logou e quem buscou
                    acessos = df_filtrado[df_filtrado['Acao'] == 'Acesso']
                    buscas = df_filtrado[df_filtrado['Acao'] == 'Busca']
                    
                    cpfs_acessaram = set(acessos['CPF'].astype(str))
                    cpfs_buscaram = set(buscas['CPF'].astype(str))
                    
                    qtd_buscas_efetivas = len(cpfs_buscaram)
                    qtd_apenas_acesso = len(cpfs_acessaram - cpfs_buscaram)
                    
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Usuários que Fizeram Buscas", qtd_buscas_efetivas)
                    col_m2.metric("Acessaram, mas NÃO buscaram", qtd_apenas_acesso)
                    
                    st.write("---")
                    st.markdown("### 📈 Termos e Demandas")
                    
                    col_g1, col_g2 = st.columns(2)
                    
                    with col_g1:
                        st.markdown("**Top 10: Ramos Mais Procurados**")
                        ramos_buscados = buscas[buscas['Termo_Ramo'] != '']['Termo_Ramo']
                        if not ramos_buscados.empty:
                            contagem_ramos = ramos_buscados.value_counts().head(10)
                            st.bar_chart(contagem_ramos)
                        else:
                            st.write("Sem buscas por Ramo no período.")
                            
                    with col_g2:
                        st.markdown("**Top 10: Prestadores Mais Procurados (Por Nome)**")
                        nomes_buscados = buscas[buscas['Termo_Nome'] != '']['Termo_Nome']
                        if not nomes_buscados.empty:
                            contagem_nomes = nomes_buscados.value_counts().head(10)
                            st.bar_chart(contagem_nomes)
                        else:
                            st.write("Sem buscas por Nome no período.")
                            
                    st.write("---")
                    st.markdown("### 🏆 Prestadores Mais Exibidos nos Resultados")
                    st.write("Quais empresas mais apareceram na tela dos síndicos nas buscas realizadas.")
                    
                    todas_empresas = []
                    for fornecedores_str in buscas['Fornecedores_Encontrados']:
                        if str(fornecedores_str).strip() != "":
                            # Divide as empresas que vieram separadas por vírgula no Log
                            empresas = [e.strip() for e in str(fornecedores_str).split(',') if e.strip() != ""]
                            todas_empresas.extend(empresas)
                            
                    if todas_empresas:
                        contagem_empresas = pd.Series(todas_empresas).value_counts().head(10)
                        st.bar_chart(contagem_empresas)
                    else:
                        st.info("Nenhuma empresa foi exibida nos resultados de busca neste período.")

    elif menu_interno == "Sugerir Contato de Prestador/Fornecedor":
        st.subheader("Indique um Profissional")
        st.write("Sua sugestão passará por uma análise técnica da administração antes de ser listada na base oficial.")
        
        with st.form("form_sugestao"):
            nome_f = st.text_input("Nome do Prestador/Fornecedor/Empresa *")
            col_t1, col_t2 = st.columns(2)
            tel1_f = col_t1.text_input("Contato Telefônico 1 (WhatsApp) *")
            tel2_f = col_t2.text_input("Contato Telefônico 2")
            email_f = st.text_input("E-mail corporativo")
            
            st.info("📋 **Instrução Obrigatória:** No campo abaixo, descreva detalhadamente quais as atividades, serviços ou produtos oferecidos. Seja específico para facilitar a homologação.")
            descricao_f = st.text_area("Descrição detalhada das atividades ou produtos *", height=100)
            
            if st.form_submit_button("Enviar Sugestão", type="primary"):
                if not nome_f or not tel1_f or not descricao_f:
                    st.error("Nome, Contato 1 e a Descrição são obrigatórios.")
                else:
                    aba_sugestoes.append_row([nome_f, tel1_f, tel2_f, email_f, descricao_f, "Pendente"])
                    st.success("✅ Indicação enviada! Agradecemos a colaboração com a Comunidade.")

    elif menu_interno == "Cadastrar Fornecedor Direto":
        st.subheader("Cadastro Direto na Base Oficial (Exclusivo Administrador)")
        
        df_f_existentes = pd.DataFrame(aba_fornecedores.get_all_records())
        ramos_existentes = set()
        if not df_f_existentes.empty:
            for i in range(1, 6):
                coluna_ramo = f'RAMO {i}'
                if coluna_ramo in df_f_existentes.columns:
                    valores = df_f_existentes[coluna_ramo].astype(str).tolist()
                    for val in valores:
                        if val.strip() != "":
                            ramos_existentes.add(val.strip())
        opcoes_ramos_oficiais = sorted(list(ramos_existentes))

        with st.form("form_cadastro_direto"):
            nome_f = st.text_input("Nome da Empresa/Prestador *")
            col_t1, col_t2 = st.columns(2)
            tel1_f = col_t1.text_input("Contato Telefônico 1 *")
            tel2_f = col_t2.text_input("Contato Telefônico 2")
            email_f = st.text_input("E-mail")
            
            ramos_selecionados = st.multiselect(
                "Selecione os Ramos de Atuação Oficiais (Máx. 5) *", 
                options=opcoes_ramos_oficiais, 
                max_selections=5
            )
            
            novo_ramo = st.text_input("Cadastrar Novo Ramo (Caso não exista na lista acima):")
            
            st.write("")
            if st.form_submit_button("✅ Cadastrar Fornecedor na Planilha", type="primary"):
                lista_final = ramos_selecionados.copy()
                if novo_ramo.strip() != "":
                    novos = [r.strip() for r in novo_ramo.split(",") if r.strip() != ""]
                    lista_final.extend(novos)
                
                while len(lista_final) < 5:
                    lista_final.append("")
                lista_final = lista_final[:5]
                
                edit_r1, edit_r2, edit_r3, edit_r4, edit_r5 = lista_final
                
                if not nome_f or not tel1_f or not edit_r1:
                    st.error("Nome, Contato 1 e pelo menos um Ramo de Atuação são obrigatórios.")
                else:
                    aba_fornecedores.append_row([
                        nome_f, tel1_f, tel2_f, email_f, 
                        edit_r1, edit_r2, edit_r3, edit_r4, edit_r5, 0
                    ])
                    st.success(f"Fornecedor '{nome_f}' inserido com sucesso na base de dados!")

    elif menu_interno == "Aprovar Sugestões":
        st.subheader("Painel de Homologação (Administrativo)")
        
        df_f_existentes = pd.DataFrame(aba_fornecedores.get_all_records())
        ramos_existentes = set()
        if not df_f_existentes.empty:
            for i in range(1, 6):
                coluna_ramo = f'RAMO {i}'
                if coluna_ramo in df_f_existentes.columns:
                    valores = df_f_existentes[coluna_ramo].astype(str).tolist()
                    for val in valores:
                        if val.strip() != "":
                            ramos_existentes.add(val.strip())
        opcoes_ramos_oficiais = sorted(list(ramos_existentes))

        df_sugestoes = pd.DataFrame(aba_sugestoes.get_all_records())
        if not df_sugestoes.empty:
            pendentes = df_sugestoes[df_sugestoes['status'] == 'Pendente']
            
            if pendentes.empty:
                st.success("Tudo limpo! Não há sugestões pendentes.")
            else:
                for i, row in pendentes.iterrows():
                    with st.expander(f"📌 Analisar Indicação: {row.get('nome', 'Sem nome')} ", expanded=True):
                        st.markdown("**Relato do usuário:**")
                        st.info(row.get('descricao', 'Sem descrição'))
                        
                        with st.form(f"form_aprovar_{i}"):
                            edit_nome = st.text_input("Nome", value=str(row.get('nome', '')))
                            col_a, col_b = st.columns(2)
                            edit_t1 = col_a.text_input("Contato 1", value=str(row.get('contato_1', '')))
                            edit_t2 = col_b.text_input("Contato 2", value=str(row.get('contato_2', '')))
                            edit_email = st.text_input("E-mail", value=str(row.get('email', '')))
                            
                            st.markdown("#### Classificação Oficial")
                            
                            ramos_selecionados = st.multiselect(
                                "Selecione na base existente (Máx. 5):", 
                                options=opcoes_ramos_oficiais, 
                                max_selections=5
                            )
                            
                            novo_ramo = st.text_input("Criar Novo Ramo (Será adicionado ao banco de dados):")
                            
                            st.write("") 
                            col_btn1, col_btn2 = st.columns(2)
                            btn_aprovar = col_btn1.form_submit_button("✅ Aprovar e Publicar", type="primary")
                            btn_rejeitar = col_btn2.form_submit_button("❌ Rejeitar e Descartar")
                            
                            if btn_aprovar:
                                lista_final = ramos_selecionados.copy()
                                if novo_ramo.strip() != "":
                                    novos = [r.strip() for r in novo_ramo.split(",") if r.strip() != ""]
                                    lista_final.extend(novos)
                                
                                while len(lista_final) < 5:
                                    lista_final.append("")
                                lista_final = lista_final[:5]
                                
                                edit_r1, edit_r2, edit_r3, edit_r4, edit_r5 = lista_final
                                
                                if not edit_nome or not edit_t1 or not edit_r1:
                                    st.error("Preencha Nome, Contato 1 e classifique pelo menos um Ramo.")
                                else:
                                    aba_fornecedores.append_row([
                                        edit_nome, edit_t1, edit_t2, edit_email, 
                                        edit_r1, edit_r2, edit_r3, edit_r4, edit_r5, 0
                                    ])
                                    aba_sugestoes.update_cell(i + 2, 6, "Aprovado")
                                    st.success(f"Homologação concluída!")
                                    st.rerun()
                                    
                            if btn_rejeitar:
                                aba_sugestoes.update_cell(i + 2, 6, "Rejeitado")
                                st.warning("Descartado com sucesso.")
                                st.rerun()
        else:
            st.success("Não há registros de sugestões na planilha.")

    elif menu_interno == "Administrar Prioridades":
        st.subheader("Painel de Patrocinadores / Destaques")
        st.write("Contas com prioridade '1' aparecerão fixadas no topo dos resultados de busca.")
        df_forn = pd.DataFrame(aba_fornecedores.get_all_records())
        if not df_forn.empty:
            col_nomes = aba_fornecedores.row_values(1)
            try:
                indice_coluna_prio = col_nomes.index("PRIORIDADE") + 1
            except ValueError:
                indice_coluna_prio = 10 
                
            for i, row in df_forn.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3,1])
                    nome_display = str(row.get('NOME', 'Sem nome'))
                    ramo_display = str(row.get('RAMO 1', 'Sem ramo'))
                    
                    col1.markdown(f"**{nome_display}**<br>Ramo: {ramo_display}", unsafe_allow_html=True)
                    
                    valor_atual = 0
                    if 'PRIORIDADE' in row and str(row['PRIORIDADE']).strip().isdigit():
                        valor_atual = int(row['PRIORIDADE'])
                    
                    nova_prio = col2.selectbox("Prioridade", [0, 1], index=[0, 1].index(valor_atual), key=f"prio_{i}")
                    
                    if nova_prio != valor_atual:
                        aba_fornecedores.update_cell(i + 2, indice_coluna_prio, nova_prio)
                        st.success("Status atualizado!")
                        st.rerun()
