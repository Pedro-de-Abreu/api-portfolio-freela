from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Annotated

# --- 1. Modelos de Dados (Schemas) ---

class UsuarioCriar(SQLModel):
    nome: str
    email: str = Field(index=True)
    senha: str

class Usuario(UsuarioCriar, table=True):
    id: int | None = Field(default=None, primary_key=True)

class UsuarioAtualizar(SQLModel):
    nome: str | None = None
    email: str | None = None
    senha: str | None = None

# --- 2. Configuração do Banco de Dados ---

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# echo=True é útil para debug, mostra os comandos SQL no terminal
engine = create_engine(sqlite_url, echo=True) 

def criar_db_e_tabelas():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

DbSession = Annotated[Session, Depends(get_session)]

# --- 3. Instância da API ---

app = FastAPI(
    title="API de Portfólio",
    version="0.1.0",
)

@app.on_event("startup")
def on_startup():
    criar_db_e_tabelas()

# --- 4. Endpoints CRUD ---

@app.get("/", tags=["Health Check"])
def ler_raiz():
    # Endpoint de "health check" para verificar se a API está no ar
    return {"status": "API no ar!"}

@app.post("/usuarios", tags=["Usuários"])
def criar_usuario(usuario_input: UsuarioCriar, session: DbSession):
    usuario_db = Usuario.model_validate(usuario_input)
    
    try:
        session.add(usuario_db)
        session.commit()
        session.refresh(usuario_db)
        return usuario_db
    except Exception as e:
        session.rollback()
        # Em um app de produção, aqui faríamos o log do erro 'e'
        raise e

@app.get("/usuarios", tags=["Usuários"])
def ler_usuarios(session: DbSession):
    consulta = select(Usuario)
    usuarios = session.exec(consulta).all()
    return usuarios

@app.get("/usuarios/{id_usuario}", tags=["Usuários"])
def ler_usuario_por_id(id_usuario: int, session: DbSession):
    usuario = session.get(Usuario, id_usuario)
    if not usuario:
        # Em um app real, retornaríamos um erro 404 (Not Found)
        return {"erro": "Usuário não encontrado"}
    return usuario

@app.put("/usuarios/{id_usuario}", tags=["Usuários"])
def atualizar_usuario(id_usuario: int, usuario_update: UsuarioAtualizar, session: DbSession):
    usuario_db = session.get(Usuario, id_usuario)
    
    if not usuario_db:
        return {"erro": "Usuário não encontrado"}
            
    # Usa exclude_unset=True para atualizar só os campos que foram enviados
    update_data = usuario_update.model_dump(exclude_unset=True)
    
    for chave, valor in update_data.items():
        setattr(usuario_db, chave, valor)
            
    session.add(usuario_db)
    session.commit()
    session.refresh(usuario_db)
    
    return usuario_db

@app.delete("/usuarios/{id_usuario}", tags=["Usuários"])
def apagar_usuario(id_usuario: int, session: DbSession):
    usuario = session.get(Usuario, id_usuario)
    
    if not usuario:
        return {"erro": "Usuário não encontrado"}
            
    session.delete(usuario)
    session.commit()
    
    return {"mensagem": "Usuário apagado com sucesso!"}
