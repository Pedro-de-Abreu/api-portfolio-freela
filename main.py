from fastapi import FastAPI, Depends  
from sqlmodel import SQLModel, Field, create_engine, Session, select  
from typing import Annotated  


# 1. O modelo de ENTRADA (sem 'id')
class UsuarioCriar(SQLModel):
    nome: str
    email: str = Field(index=True)
    senha: str

# --- ESTA É A NOVA CLASSE ---
# O modelo de ATUALIZAÇÃO.
# Todos os campos são opcionais ('| None = None'),
# pois o usuário pode querer atualizar só o nome, ou só a senha.
class UsuarioAtualizar(SQLModel):
    nome: str | None = None
    email: str | None = None
    senha: str | None = None

# 2. O modelo do BANCO DE DADOS (com 'id', que herda da 'UsuarioCriar')
#    Repare que ela NÃO TEM 'nome', 'email' ou 'senha' dentro dela,
#    pois ela já herda isso da classe de cima.
class Usuario(UsuarioCriar, table=True):
    id: int | None = Field(default=None, primary_key=True)

# --- FIM DO BLOCO ---

# --- 2. Configuração do Banco de Dados ---
# "sqlite:///database.db" significa que nosso banco será um arquivo chamado 'database.db'
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# O 'engine' é o "conector" que sabe falar com o banco de dados SQLite.
engine = create_engine(sqlite_url, echo=True) # 'echo=True' mostra os comandos SQL no terminal (ótimo para debug)

# Esta função "gera" uma sessão com o banco de dados para cada
# requisição que precisar dela, e garante que a sessão seja fechada no final.
def get_session():
    with Session(engine) as session:
        yield session

# 'Annotated[Session, Depends(get_session)]' é a nova forma do FastAPI
# de dizer: "Para esta variável, execute a função get_session() e 
# injete o resultado (a sessão) aqui."
DbSession = Annotated[Session, Depends(get_session)]

# Função que cria as tabelas no banco de dados
def criar_db_e_tabelas():
    # SQLModel.metadata.create_all(engine) vai olhar todas as classes que herdam de SQLModel
    # (como a classe 'Usuario') e vai criar as tabelas no banco.
    SQLModel.metadata.create_all(engine)

# --- 3. Inicialização do Aplicativo FastAPI ---
# O 'app' é a instância principal da nossa API.
app = FastAPI()

# --- 4. Evento de Inicialização ---
# Este comando faz com que a função 'criar_db_e_tabelas'
# seja executada UMA VEZ, assim que a API "ligar".
@app.on_event("startup")
def on_startup():
    criar_db_e_tabelas()

# --- 5. Nosso Primeiro Endpoint (Rota) ---
# Este é um "endpoint" de teste.
# Quando você acessar http://127.0.0.1:8000/ no seu navegador,
# esta função será executada.
@app.get("/")
def ler_raiz():
    return {"mensagem": "Olá! Minha API de Cadastro está no ar!"}


# --- 6. Endpoint para CRIAR um Usuário (POST) ---

@app.post("/usuarios")
def criar_usuario(usuario_input: UsuarioCriar, session: DbSession):
    # 'usuario_input: UsuarioCriar' -> Agora a API SÓ ACEITA
    # o nosso modelo novo, que não tem 'id'.
    
    try:
        # 1. Criamos um objeto 'Usuario' (do banco)
        #    a partir dos dados do 'usuario_input'.
        usuario_db = Usuario.model_validate(usuario_input)

        # 2. Agora, o 'usuario_db' tem nome, email, senha,
        #    mas o 'id' dele é 'None' (o padrão que definimos).
        
        # 3. Adicionamos este novo objeto à sessão
        session.add(usuario_db)
        # 4. Salvamos no banco (Agora o SQLite vai gerar o ID 1)
        session.commit()
        # 5. Atualizamos o objeto 'usuario_db' com o ID que o banco gerou
        session.refresh(usuario_db)
        
        # 6. Retornamos o usuário completo (com o ID novo)
        return usuario_db
    
    except Exception as e:
        session.rollback()
        raise e


# --- 7. Endpoint para LER TODOS os Usuários (GET) ---

@app.get("/usuarios")
def ler_usuarios(session: DbSession):
    # Usamos a função 'select()' do SQLModel para criar uma consulta
    # que seleciona todos os objetos da classe 'Usuario'.
    consulta = select(Usuario)
    
    # 'session.exec()' executa a consulta no banco de dados
    # 'all()' pega todos os resultados e os coloca em uma lista.
    usuarios = session.exec(consulta).all()
    
    # Retornamos a lista de usuários. O FastAPI vai convertê-la
    # para JSON automaticamente.
    return usuarios

# --- Fim do Bloco ---

# --- 8. Endpoint para LER UM Usuário (por ID) ---

@app.get("/usuarios/{id_usuario}")
def ler_usuario_por_id(id_usuario: int, session: DbSession):
    # 'id_usuario: int' -> O FastAPI entende que o valor vindo
    # na URL (ex: /usuarios/1) deve ser convertido para um inteiro.
    
    # 'session.get()' é o atalho do SQLModel para buscar um item
    # pela sua chave primária (o 'id'). É rápido e direto.
    usuario = session.get(Usuario, id_usuario)
    
    # Se o 'session.get()' não encontrar ninguém com esse ID,
    # ele retornará 'None'.
    if not usuario:
        # Em um app real, retornaríamos um erro 404 - Not Found
        # Aqui, vamos apenas retornar uma mensagem simples
        return {"erro": "Usuário não encontrado"}
        
    return usuario

# --- Fim do Bloco ---

# --- 9. Endpoint para APAGAR um Usuário (por ID) ---

@app.delete("/usuarios/{id_usuario}")
def apagar_usuario(id_usuario: int, session: DbSession):
    # 'id_usuario: int' -> Recebemos o ID pela URL.
    
    # 1. Primeiro, encontramos o usuário que queremos apagar.
    usuario = session.get(Usuario, id_usuario)
    
    # 2. Verificamos se ele realmente existe.
    if not usuario:
        # Se não existir, retornamos um erro.
        return {"erro": "Usuário não encontrado"}
        
    # 3. Se ele existe, usamos o 'session.delete()' para apagá-lo
    session.delete(usuario)
    
    # 4. Damos o 'commit()' para confirmar a exclusão no banco
    session.commit()
    
    # 5. Retornamos uma mensagem de sucesso
    return {"mensagem": "Usuário apagado com sucesso!"}

# --- Fim do Bloco ---

# --- 10. Endpoint para ATUALIZAR um Usuário (por ID) ---

@app.put("/usuarios/{id_usuario}")
def atualizar_usuario(id_usuario: int, usuario_update: UsuarioAtualizar, session: DbSession):
    # 'id_usuario' vem da URL
    # 'usuario_update' vem do corpo (body) da requisição
    
    # 1. Primeiro, encontramos o usuário que queremos editar.
    usuario_db = session.get(Usuario, id_usuario)
    
    # 2. Verificamos se ele realmente existe.
    if not usuario_db:
        return {"erro": "Usuário não encontrado"}
        
    # 3. Pegamos os dados do 'usuario_update' (do body)
    #    'exclude_unset=True' é um truque para só pegar os campos
    #    que o usuário realmente enviou (e ignorar os 'None').
    update_data = usuario_update.model_dump(exclude_unset=True)
    
    # 4. Atualizamos o objeto do banco ('usuario_db')
    #    com os dados novos ('update_data').
    #    O 'setattr' é o jeito do Python de fazer:
    #    usuario_db.nome = "Novo Nome"
    #    usuario_db.email = "novo@email.com"
    for chave, valor in update_data.items():
        setattr(usuario_db, chave, valor)
        
    # 5. Adicionamos o objeto modificado e damos o commit
    session.add(usuario_db)
    session.commit()
    # 6. Atualizamos o objeto para pegar a versão final do banco
    session.refresh(usuario_db)
    
    # 7. Retornamos o usuário com os dados atualizados
    return usuario_db

# --- Fim do Bloco ---