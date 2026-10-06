# Hundir la Flota

Juego por turnos contra IA, con modo terminal y una web local para estudiar la
ejecucion interna.

## Modo terminal

```powershell
python play.py
```

## Web local

Instala dependencias Python:

```powershell
pip install -r requirements.txt
```

Arranca la API:

```powershell
python -m uvicorn backend.api:app --reload
```

En otra terminal, instala y arranca el frontend:

```powershell
cd frontend
npm install
npm run dev
```

La web quedara disponible en `http://127.0.0.1:5173`.
