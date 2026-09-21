"""Punto de entrada local. Ejecuta: python run.py"""
import uvicorn

if __name__ == '__main__':
    print('\nCirugía Ágil: abre http://127.0.0.1:8000\nDetener: Ctrl+C\n')
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, reload=False)
