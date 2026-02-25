import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.concurrency import run_in_threadpool

# Ensure we can import from local source if running as script
import sys
import os
sys.path.append(os.path.abspath("../../../../src"))

from models import setup_database, seed_data
from schema import schema, UserLoader, PostLoader, PostsByUserLoader, CommentsByPostLoader

app = FastAPI()

@app.on_event("startup")
def on_startup():
    setup_database()
    seed_data()

class Loaders:
    def __init__(self):
        self.user_loader = UserLoader()
        self.post_loader = PostLoader()
        self.posts_by_user_loader = PostsByUserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()

@app.post("/graphql")
async def graphql_server(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
        
    query = data.get("query")
    variables = data.get("variables")
    operation_name = data.get("operationName")
    
    if not query:
        return JSONResponse({"errors": ["No query provided"]}, status_code=400)

    # Initialize loaders for this request
    context = {"request": request, "loaders": Loaders()}
    
    # Execute query asynchronously
    result = await schema.execute_async(
        query,
        variable_values=variables,
        context_value=context,
        operation_name=operation_name
    )
    
    response_data = {}
    if result.data:
        response_data["data"] = result.data
    if result.errors:
        # Format errors
        response_data["errors"] = [{"message": str(e)} for e in result.errors]
        
    return JSONResponse(response_data)

@app.get("/graphql")
async def graphiql_interface():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body {
            height: 100%;
            margin: 0;
            width: 100%;
            overflow: hidden;
          }
          #graphiql {
            height: 100vh;
          }
        </style>
        <script
          crossorigin
          src="https://unpkg.com/react@18/umd/react.development.js"
        ></script>
        <script
          crossorigin
          src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"
        ></script>
        <script
          crossorigin
          src="https://unpkg.com/graphiql/graphiql.min.js"
        ></script>
        <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
      </head>
      <body>
        <div id="graphiql">Loading...</div>
        <script>
          const root = ReactDOM.createRoot(document.getElementById('graphiql'));
          const fetcher = GraphiQL.createFetcher({
            url: '/graphql',
          });
          root.render(
            React.createElement(GraphiQL, {
              fetcher: fetcher,
              defaultEditorToolsVisibility: true,
            })
          );
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html)

if __name__ == "__main__":
    print("Starting GraphQL Server at http://localhost:8000/graphql")
    uvicorn.run(app, host="0.0.0.0", port=8000)
