# Deployment stabilization — 2026-09-29

The original deployment logs show Streamlit successfully installed dependencies and started its server, but then repeatedly logged `ModuleNotFoundError: No module named 'torchvision'` while inspecting the Transformers package. The original dependency chain included `sentence-transformers`, which pulled in PyTorch/Transformers and a large CUDA stack.

This fixed repository removes that chain entirely.

## New embedding path

`documents/embeddings.py` uses Google `gemini-embedding-2` with `output_dimensionality=384`, matching the existing PostgreSQL `vector(384)` column. Google documents 128–3072 supported dimensions and recommends larger sizes such as 768/1536/3072; 384 is deliberately retained here to avoid a database migration during stabilization.

## Important

Do NOT rerun the existing Neon schema on the current database.
