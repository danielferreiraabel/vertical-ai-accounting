"""
Módulo principal da API para a IA Vertical de Contabilidade.
"""

import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uvicorn
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, date, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Importar módulos da aplicação
from app.models.document_classifier import DocumentClassifier, train_sample_model
from app.models.chatbot import ContabilidadeChatbot
from app.models.tax_analyzer import AnalisadorTributario, OportunidadeTributaria
from app.services.report_service import ReportGenerator, FinancialData
from app.services.bank_service import ConciliacaoBancaria
from app.services.deadline_service import GestorObrigacoes, Obrigacao
import db

# Configurações de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "chave_secreta_temporaria_deve_ser_alterada_em_producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuração de criptografia de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Modelos Pydantic para autenticação
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: str
    nome: str
    cargo: Optional[str] = None
    empresa_id: Optional[int] = None

class UserCreate(UserBase):
    senha: str

class User(UserBase):
    id: int
    ativo: bool
    
    class Config:
        orm_mode = True

# Criar aplicação FastAPI
app = FastAPI(
    title="IA Vertical para Contabilidade",
    description="API para IA especializada em contabilidade",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretório para uploads e dados
os.makedirs("./uploads", exist_ok=True)
os.makedirs("./data", exist_ok=True)

# Inicializar componentes
document_classifier = None
chatbot = ContabilidadeChatbot()
report_generator = ReportGenerator(output_dir="./data/reports")
conciliacao_bancaria = ConciliacaoBancaria()
gestor_obrigacoes = GestorObrigacoes()
analisador_tributario = AnalisadorTributario()

# Funções de autenticação
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(db.Usuario).filter(db.Usuario.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.senha_hash):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(db.get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.ativo:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user

# Rota para autenticação
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db.get_db_session)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Atualizar último acesso
    user.ultimo_acesso = datetime.now()
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

# Rota raiz
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>IA Vertical para Contabilidade</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #2c3e50; }
                h2 { color: #3498db; margin-top: 30px; }
                ul { margin-bottom: 30px; }
                li { margin-bottom: 10px; }
                .footer { margin-top: 50px; font-size: 0.8em; color: #7f8c8d; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>IA Vertical para Contabilidade</h1>
                <p>Bem-vindo à API da IA Vertical para Contabilidade. Esta API oferece diversas funcionalidades para automatizar e otimizar processos contábeis.</p>
                
                <h2>Funcionalidades Disponíveis:</h2>
                <ul>
                    <li><strong>Classificação de Documentos Fiscais:</strong> Identifica e categoriza automaticamente notas fiscais, recibos e outros documentos contábeis.</li>
                    <li><strong>Geração de Relatórios Financeiros:</strong> Cria relatórios detalhados de balanço, DRE e fluxo de caixa em segundos.</li>
                    <li><strong>Chatbot Contábil:</strong> Assistente virtual treinado em linguagem contábil para atendimento a clientes.</li>
                    <li><strong>Conciliação Bancária Automática:</strong> Compara e reconcilia automaticamente transações bancárias com registros contábeis.</li>
                    <li><strong>Gestão de Prazos e Obrigações:</strong> Sistema de alertas e monitoramento de obrigações fiscais para evitar multas.</li>
                    <li><strong>Diagnóstico de Oportunidades Tributárias:</strong> Análise inteligente para identificar oportunidades de economia fiscal.</li>
                </ul>
                
                <h2>Documentação da API:</h2>
                <p>Para acessar a documentação completa da API, visite <a href="/docs">/docs</a>.</p>
                
                <div class="footer">
                    <p>IA Vertical para Contabilidade - Versão 1.0.0</p>
                </div>
            </div>
        </body>
    </html>
    """

# Rotas para usuários
@app.post("/usuarios/", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(db.get_db_session)):
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    hashed_password = get_password_hash(user.senha)
    db_user = db.Usuario(
        email=user.email,
        nome=user.nome,
        senha_hash=hashed_password,
        cargo=user.cargo,
        empresa_id=user.empresa_id,
        ativo=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/usuarios/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Rotas para classificação de documentos
@app.post("/documentos/classificar", tags=["Documentos"])
async def classificar_documento(
    arquivo: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    global document_classifier
    
    # Inicializar classificador se necessário
    if document_classifier is None:
        try:
            # Tentar carregar modelo pré-treinado
            model_path = "./data/document_classifier_model.pkl"
            if os.path.exists(model_path):
                document_classifier = DocumentClassifier(model_path=model_path)
            else:
                # Treinar modelo de exemplo
                document_classifier = train_sample_model()
                # Salvar modelo para uso futuro
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                document_classifier._save_model(model_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao inicializar classificador: {str(e)}")
    
    # Salvar arquivo temporariamente
    file_path = f"./uploads/{arquivo.filename}"
    with open(file_path, "wb") as f:
        f.write(await arquivo.read())
    
    try:
        # Classificar documento
        resultado = document_classifier.predict(file_path)
        
        # Salvar documento no banco de dados
        db_session = db.get_db_session()
        documento = db.Documento(
            nome=arquivo.filename,
            tipo=resultado["category"],
            caminho_arquivo=file_path,
            processado=True,
            categoria=resultado["category"],
            conteudo_texto=resultado.get("extracted_text", ""),
            empresa_id=current_user.empresa_id
        )
        db_session.add(documento)
        db_session.commit()
        db_session.refresh(documento)
        db_session.close()
        
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao classificar documento: {str(e)}")
    finally:
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)

# Rotas para chatbot
@app.post("/chatbot/mensagem", tags=["Chatbot"])
async def processar_mensagem(
    mensagem: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        resposta = chatbot.process_message(mensagem)
        
        # Salvar mensagem no banco de dados
        chat_mensagem = db.ChatMensagem(
            usuario_id=current_user.id,
            mensagem=mensagem,
            resposta=resposta["response"],
            categoria=resposta.get("category"),
            confianca=resposta.get("confidence")
        )
        db_session.add(chat_mensagem)
        db_session.commit()
        
        return resposta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {str(e)}")

@app.get("/chatbot/historico", tags=["Chatbot"])
async def obter_historico_chat(
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        # Buscar histórico do usuário no banco de dados
        mensagens = db_session.query(db.ChatMensagem).filter(
            db.ChatMensagem.usuario_id == current_user.id
        ).order_by(db.ChatMensagem.timestamp.desc()).limit(50).all()
        
        historico = [
            {
                "id": msg.id,
                "mensagem": msg.mensagem,
                "resposta": msg.resposta,
                "categoria": msg.categoria,
                "confianca": msg.confianca,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in mensagens
        ]
        
        return {"historico": historico}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter histórico: {str(e)}")

# Rotas para relatórios financeiros
@app.post("/relatorios/balanco", tags=["Relatórios"])
async def gerar_balanco(
    dados: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Converter dados para objeto FinancialData
        financial_data = FinancialData(
            receitas=dados.get("receitas", {}),
            despesas=dados.get("despesas", {}),
            ativos=dados.get("ativos", {}),
            passivos=dados.get("passivos", {}),
            patrimonio_liquido=dados.get("patrimonio_liquido", {}),
            periodo=dados.get("periodo", ""),
            empresa=dados.get("empresa", "")
        )
        
        # Gerar relatório
        relatorio_path = report_generator.generate_balance_sheet(financial_data)
        
        # Retornar caminho do relatório
        return {"relatorio_path": relatorio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar balanço: {str(e)}")

@app.post("/relatorios/dre", tags=["Relatórios"])
async def gerar_dre(
    dados: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Converter dados para objeto FinancialData
        financial_data = FinancialData(
            receitas=dados.get("receitas", {}),
            despesas=dados.get("despesas", {}),
            ativos=dados.get("ativos", {}),
            passivos=dados.get("passivos", {}),
            patrimonio_liquido=dados.get("patrimonio_liquido", {}),
            periodo=dados.get("periodo", ""),
            empresa=dados.get("empresa", "")
        )
        
        # Gerar relatório
        relatorio_path = report_generator.generate_income_statement(financial_data)
        
        # Retornar caminho do relatório
        return {"relatorio_path": relatorio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DRE: {str(e)}")

@app.post("/relatorios/fluxo-caixa", tags=["Relatórios"])
async def gerar_fluxo_caixa(
    dados: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Extrair dados
        fluxo_data = dados.get("fluxo_data", {})
        empresa = dados.get("empresa", "")
        periodo = dados.get("periodo", "")
        
        # Gerar relatório
        relatorio_path = report_generator.generate_cash_flow(fluxo_data, empresa, periodo)
        
        # Retornar caminho do relatório
        return {"relatorio_path": relatorio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar fluxo de caixa: {str(e)}")

# Rotas para conciliação bancária
@app.post("/conciliacao/importar-extrato", tags=["Conciliação Bancária"])
async def importar_extrato(
    arquivo: UploadFile = File(...),
    mapeamento: str = Form(...),
    formato_data: str = Form("dd/mm/yyyy"),
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        # Salvar arquivo temporariamente
        file_path = f"./uploads/{arquivo.filename}"
        with open(file_path, "wb") as f:
            f.write(await arquivo.read())
        
        # Converter mapeamento para dicionário
        mapeamento_dict = json.loads(mapeamento)
        
        # Converter formato de data
        formato_data_python = formato_data.replace("dd", "%d").replace("mm", "%m").replace("yyyy", "%Y")
        
        # Importar extrato
        count = conciliacao_bancaria.importar_extrato_bancario(file_path, mapeamento_dict, formato_data_python)
        
        # Salvar transações no banco de dados
        for transacao in conciliacao_bancaria.transacoes_bancarias:
            db_transacao = db.TransacaoBancaria(
                data=transacao.data,
                descricao=transacao.descricao,
                valor=transacao.valor,
                tipo=transacao.tipo,
                id_transacao=transacao.id_transacao,
                conciliada=transacao.conciliada,
                id_correspondente=transacao.id_correspondente,
                empresa_id=current_user.empresa_id
            )
            db_session.add(db_transacao)
        
        db_session.commit()
        
        return {"transacoes_importadas": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao importar extrato: {str(e)}")
    finally:
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/conciliacao/importar-lancamentos", tags=["Conciliação Bancária"])
async def importar_lancamentos(
    arquivo: UploadFile = File(...),
    mapeamento: str = Form(...),
    formato_data: str = Form("dd/mm/yyyy"),
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        # Salvar arquivo temporariamente
        file_path = f"./uploads/{arquivo.filename}"
        with open(file_path, "wb") as f:
            f.write(await arquivo.read())
        
        # Converter mapeamento para dicionário
        mapeamento_dict = json.loads(mapeamento)
        
        # Converter formato de data
        formato_data_python = formato_data.replace("dd", "%d").replace("mm", "%m").replace("yyyy", "%Y")
        
        # Importar lançamentos
        count = conciliacao_bancaria.importar_lancamentos_contabeis(file_path, mapeamento_dict, formato_data_python)
        
        # Salvar lançamentos no banco de dados
        for lancamento in conciliacao_bancaria.lancamentos_contabeis:
            db_lancamento = db.LancamentoContabil(
                data=lancamento.data,
                descricao=lancamento.descricao,
                valor=lancamento.valor,
                tipo=lancamento.tipo,
                id_lancamento=lancamento.id_lancamento,
                conta_contabil=lancamento.conta_contabil,
                conciliado=lancamento.conciliado,
                id_correspondente=lancamento.id_correspondente,
                empresa_id=current_user.empresa_id
            )
            db_session.add(db_lancamento)
        
        db_session.commit()
        
        return {"lancamentos_importados": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao importar lançamentos: {str(e)}")
    finally:
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/conciliacao/conciliar-automatico", tags=["Conciliação Bancária"])
async def conciliar_automatico(
    limiar: float = Query(0.7, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_active_user)
):
    try:
        conciliacoes = conciliacao_bancaria.conciliar_automaticamente(limiar)
        return {"conciliacoes": conciliacoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conciliar: {str(e)}")

@app.get("/conciliacao/relatorio", tags=["Conciliação Bancária"])
async def relatorio_conciliacao(
    current_user: User = Depends(get_current_active_user)
):
    try:
        relatorio = conciliacao_bancaria.gerar_relatorio_conciliacao()
        return relatorio
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

# Rotas para gestão de prazos e obrigações
@app.post("/obrigacoes/adicionar", tags=["Obrigações Fiscais"])
async def adicionar_obrigacao(
    dados: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        # Converter data de vencimento
        data_vencimento = datetime.fromisoformat(dados["data_vencimento"]).date()
        
        # Converter data de conclusão, se existir
        data_conclusao = None
        if "data_conclusao" in dados and dados["data_conclusao"]:
            data_conclusao = datetime.fromisoformat(dados["data_conclusao"]).date()
        
        # Criar objeto Obrigacao para o gestor
        obrigacao = Obrigacao(
            id=dados["id"],
            nome=dados["nome"],
            descricao=dados["descricao"],
            periodicidade=dados["periodicidade"],
            data_vencimento=data_vencimento,
            status=dados["status"],
            prioridade=dados["prioridade"],
            responsavel=dados["responsavel"],
            empresa=dados.get("empresa", current_user.nome),
            regime_tributario=dados["regime_tributario"],
            categoria=dados["categoria"],
            valor_multa=dados.get("valor_multa"),
            data_conclusao=data_conclusao,
            observacoes=dados.get("observacoes")
        )
        
        # Adicionar obrigação ao gestor
        id_obrigacao = gestor_obrigacoes.adicionar_obrigacao(obrigacao)
        
        # Criar objeto Obrigacao para o banco de dados
        db_obrigacao = db.Obrigacao(
            nome=dados["nome"],
            descricao=dados["descricao"],
            periodicidade=dados["periodicidade"],
            data_vencimento=data_vencimento,
            status=dados["status"],
            prioridade=dados["prioridade"],
            responsavel=dados["responsavel"],
            empresa_id=current_user.empresa_id,
            categoria=dados["categoria"],
            valor_multa=dados.get("valor_multa"),
            data_conclusao=data_conclusao,
            observacoes=dados.get("observacoes")
        )
        
        db_session.add(db_obrigacao)
        db_session.commit()
        
        return {"id_obrigacao": id_obrigacao}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar obrigação: {str(e)}")

@app.get("/obrigacoes/proximos-dias", tags=["Obrigações Fiscais"])
async def obrigacoes_proximos_dias(
    dias: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        # Buscar obrigações do banco de dados
        hoje = date.today()
        data_limite = hoje + timedelta(days=dias)
        
        db_obrigacoes = db_session.query(db.Obrigacao).filter(
            db.Obrigacao.empresa_id == current_user.empresa_id,
            db.Obrigacao.data_vencimento >= hoje,
            db.Obrigacao.data_vencimento <= data_limite,
            db.Obrigacao.status != "concluida"
        ).all()
        
        # Converter para formato serializável
        obrigacoes_dict = [
            {
                "id": o.id,
                "nome": o.nome,
                "descricao": o.descricao,
                "data_vencimento": o.data_vencimento.isoformat(),
                "status": o.status,
                "prioridade": o.prioridade,
                "responsavel": o.responsavel,
                "empresa_id": o.empresa_id,
                "categoria": o.categoria
            }
            for o in db_obrigacoes
        ]
        
        return {"obrigacoes": obrigacoes_dict}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter obrigações: {str(e)}")

@app.get("/obrigacoes/alertas", tags=["Obrigações Fiscais"])
async def gerar_alertas_obrigacoes(
    current_user: User = Depends(get_current_active_user)
):
    try:
        alertas = gestor_obrigacoes.gerar_alertas()
        return {"alertas": alertas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar alertas: {str(e)}")

@app.get("/obrigacoes/calendario/{ano}/{mes}", tags=["Obrigações Fiscais"])
async def calendario_mensal(
    ano: int,
    mes: int,
    current_user: User = Depends(get_current_active_user)
):
    try:
        calendario = gestor_obrigacoes.gerar_calendario_mensal(ano, mes)
        return calendario
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar calendário: {str(e)}")

# Rotas para análise tributária
@app.post("/tributario/analisar", tags=["Análise Tributária"])
async def analisar_oportunidades(
    dados_empresa: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db_session: Session = Depends(db.get_db_session)
):
    try:
        oportunidades = analisador_tributario.analisar_oportunidades(dados_empresa)
        
        # Salvar oportunidades no banco de dados
        for op in oportunidades:
            db_oportunidade = db.OportunidadeTributaria(
                nome=op["nome"],
                descricao=op["descricao"],
                economia_estimada=op["economia_estimada"],
                complexidade=op["complexidade"],
                risco=op["risco"],
                categoria=op["categoria"],
                prazo_implementacao=op["prazo_implementacao"],
                status=op["status"],
                empresa_id=current_user.empresa_id
            )
            db_session.add(db_oportunidade)
        
        db_session.commit()
        
        return {"oportunidades": oportunidades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar oportunidades: {str(e)}")

@app.post("/tributario/calcular-roi", tags=["Análise Tributária"])
async def calcular_roi(
    id_oportunidade: str = Form(...),
    custo_implementacao: float = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Verificar se a oportunidade existe
        if not any(o.id == id_oportunidade for o in analisador_tributario.oportunidades):
            # Se não existir, adicionar a partir do catálogo
            if id_oportunidade in analisador_tributario.catalogo_oportunidades:
                cat = analisador_tributario.catalogo_oportunidades[id_oportunidade]
                oportunidade = OportunidadeTributaria(
                    id=id_oportunidade,
                    nome=cat["nome"],
                    descricao=cat["descricao"],
                    economia_estimada=10000.0,  # Valor padrão
                    complexidade=cat["complexidade"],
                    risco=cat["risco"],
                    categoria=cat["categoria"],
                    aplicavel_regimes=cat["aplicavel_regimes"],
                    prazo_implementacao=cat["prazo_implementacao"],
                    status="identificada"
                )
                analisador_tributario.adicionar_oportunidade(oportunidade)
            else:
                raise HTTPException(status_code=404, detail=f"Oportunidade não encontrada: {id_oportunidade}")
        
        # Calcular ROI
        roi = analisador_tributario.calcular_roi_oportunidade(id_oportunidade, custo_implementacao)
        
        return roi
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular ROI: {str(e)}")

@app.get("/tributario/relatorio", tags=["Análise Tributária"])
async def relatorio_tributario(
    filtro_status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    try:
        relatorio = analisador_tributario.gerar_relatorio_oportunidades(filtro_status)
        return relatorio
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

# Inicializar banco de dados
@app.on_event("startup")
async def startup_event():
    db.initialize_database_with_sample_data()

# Iniciar servidor se executado diretamente
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

