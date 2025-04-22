"""
Módulo de banco de dados para a IA Vertical de Contabilidade.
Gerencia conexões e operações com o banco de dados.
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

# Criar base declarativa
Base = declarative_base()

# Definir modelos
class Usuario(Base):
    """Modelo para usuários do sistema."""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    senha_hash = Column(String(100), nullable=False)
    cargo = Column(String(50))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.now)
    ultimo_acesso = Column(DateTime, nullable=True)
    
    empresa = relationship("Empresa", back_populates="usuarios")

class Empresa(Base):
    """Modelo para empresas clientes."""
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=False, index=True)
    regime_tributario = Column(String(50))
    setor = Column(String(50))
    data_cadastro = Column(DateTime, default=datetime.now)
    
    usuarios = relationship("Usuario", back_populates="empresa")
    documentos = relationship("Documento", back_populates="empresa")
    obrigacoes = relationship("Obrigacao", back_populates="empresa")
    oportunidades = relationship("OportunidadeTributaria", back_populates="empresa")

class Documento(Base):
    """Modelo para documentos fiscais."""
    __tablename__ = "documentos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(50))
    caminho_arquivo = Column(String(255))
    data_upload = Column(DateTime, default=datetime.now)
    processado = Column(Boolean, default=False)
    categoria = Column(String(50))
    conteudo_texto = Column(Text, nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    
    empresa = relationship("Empresa", back_populates="documentos")

class Obrigacao(Base):
    """Modelo para obrigações fiscais."""
    __tablename__ = "obrigacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    periodicidade = Column(String(20))
    data_vencimento = Column(Date, nullable=False)
    status = Column(String(20), default="pendente")
    prioridade = Column(Integer, default=3)
    responsavel = Column(String(100))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    categoria = Column(String(50))
    valor_multa = Column(Float, nullable=True)
    data_conclusao = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)
    
    empresa = relationship("Empresa", back_populates="obrigacoes")

class OportunidadeTributaria(Base):
    """Modelo para oportunidades tributárias."""
    __tablename__ = "oportunidades_tributarias"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    economia_estimada = Column(Float)
    complexidade = Column(Integer)
    risco = Column(Integer)
    categoria = Column(String(50))
    prazo_implementacao = Column(Integer)
    status = Column(String(20), default="identificada")
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    data_identificacao = Column(DateTime, default=datetime.now)
    
    empresa = relationship("Empresa", back_populates="oportunidades")

class TransacaoBancaria(Base):
    """Modelo para transações bancárias."""
    __tablename__ = "transacoes_bancarias"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    descricao = Column(String(255))
    valor = Column(Float, nullable=False)
    tipo = Column(String(20))  # "credito" ou "debito"
    id_transacao = Column(String(100), unique=True)
    conciliada = Column(Boolean, default=False)
    id_correspondente = Column(String(100), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    
    empresa = relationship("Empresa")

class LancamentoContabil(Base):
    """Modelo para lançamentos contábeis."""
    __tablename__ = "lancamentos_contabeis"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    descricao = Column(String(255))
    valor = Column(Float, nullable=False)
    tipo = Column(String(20))  # "credito" ou "debito"
    id_lancamento = Column(String(100), unique=True)
    conta_contabil = Column(String(50))
    conciliado = Column(Boolean, default=False)
    id_correspondente = Column(String(100), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    
    empresa = relationship("Empresa")

class ChatMensagem(Base):
    """Modelo para mensagens do chatbot."""
    __tablename__ = "chat_mensagens"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text, nullable=True)
    categoria = Column(String(50), nullable=True)
    confianca = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    
    usuario = relationship("Usuario")

# Função para criar conexão com o banco de dados
def get_database_connection():
    """
    Cria e retorna uma conexão com o banco de dados.
    
    Returns:
        Tuple[Engine, Session]: Engine e Session do SQLAlchemy
    """
    # Verificar se existe variável de ambiente para a URL do banco de dados
    database_url = os.getenv("DATABASE_URL", "sqlite:///./contabilidade_ia.db")
    
    # Criar engine
    engine = create_engine(database_url)
    
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    
    # Criar sessão
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal

# Função para obter uma sessão do banco de dados
def get_db_session():
    """
    Obtém uma sessão do banco de dados.
    
    Returns:
        Session: Sessão do SQLAlchemy
    """
    _, SessionLocal = get_database_connection()
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Função para inicializar o banco de dados com dados de exemplo
def initialize_database_with_sample_data():
    """
    Inicializa o banco de dados com dados de exemplo.
    """
    engine, SessionLocal = get_database_connection()
    db = SessionLocal()
    
    try:
        # Verificar se já existem dados
        if db.query(Empresa).count() > 0:
            return
        
        # Criar empresa de exemplo
        empresa = Empresa(
            nome="Contabilidade Exemplo Ltda",
            cnpj="12.345.678/0001-90",
            regime_tributario="lucro_presumido",
            setor="servicos"
        )
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        
        # Criar usuário de exemplo
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        usuario = Usuario(
            nome="Administrador",
            email="admin@exemplo.com",
            senha_hash=pwd_context.hash("senha123"),
            cargo="Contador",
            empresa_id=empresa.id
        )
        db.add(usuario)
        
        # Criar obrigações de exemplo
        from datetime import date, timedelta
        
        hoje = date.today()
        
        obrigacoes = [
            Obrigacao(
                nome="DARF IRPJ",
                descricao="Pagamento do IRPJ mensal por estimativa",
                periodicidade="mensal",
                data_vencimento=date(hoje.year, hoje.month, 20),
                status="pendente",
                prioridade=1,
                responsavel="Administrador",
                empresa_id=empresa.id,
                categoria="federal",
                valor_multa=500.0
            ),
            Obrigacao(
                nome="GFIP",
                descricao="Entrega da GFIP mensal",
                periodicidade="mensal",
                data_vencimento=date(hoje.year, hoje.month, 7),
                status="concluida" if hoje.day > 7 else "pendente",
                prioridade=1,
                responsavel="Administrador",
                empresa_id=empresa.id,
                categoria="federal",
                valor_multa=1000.0,
                data_conclusao=date(hoje.year, hoje.month, 5) if hoje.day > 7 else None
            )
        ]
        
        for obrigacao in obrigacoes:
            db.add(obrigacao)
        
        # Commit final
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao inicializar banco de dados: {e}")
    finally:
        db.close()

# Inicializar banco de dados se este arquivo for executado diretamente
if __name__ == "__main__":
    print("Inicializando banco de dados...")
    initialize_database_with_sample_data()
    print("Banco de dados inicializado com sucesso!")



