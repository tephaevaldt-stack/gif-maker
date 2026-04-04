# 🎬 GIF Maker

Converta trechos de vídeos do **YouTube**, **TikTok** e **Instagram** em GIFs de até 20MB — sem precisar baixar o vídeo manualmente.

---

## ✅ Pré-requisitos

Você precisa ter instalado:

| Ferramenta | Para quê | Instalação |
|---|---|---|
| **Python 3** | Rodar o servidor | `brew install python3` (macOS) / já vem no Ubuntu |
| **ffmpeg** | Converter vídeo → GIF | `brew install ffmpeg` / `sudo apt install ffmpeg` |
| **yt-dlp** | Baixar vídeos | `brew install yt-dlp` / `pip3 install yt-dlp` |

### Instalação rápida

**macOS (com Homebrew):**
```bash
brew install python3 ffmpeg yt-dlp
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg python3 python3-pip
pip3 install yt-dlp
```

**Windows:**
- Instale o [Python](https://python.org/downloads/)
- Instale o [ffmpeg](https://ffmpeg.org/download.html) e adicione ao PATH
- Execute: `pip install yt-dlp`

---

## 🚀 Como usar

1. **Abra o terminal** e navegue até esta pasta:
   ```bash
   cd gif-maker
   ```

2. **Execute o script de inicialização:**
   ```bash
   bash start.sh
   ```
   *(No Windows: `python app.py`)*

3. **Abra o navegador** em: [http://localhost:5000](http://localhost:5000)

4. **Cole a URL** do vídeo (YouTube, TikTok ou Instagram público)

5. **Ajuste o range** na timeline arrastando os handles

6. **Configure** largura e FPS conforme necessário

7. **Clique em "Gerar GIF"** e aguarde

8. **Baixe o GIF** quando estiver pronto!

---

## ⚙️ Como funciona

```
URL do vídeo
    │
    ▼
yt-dlp (só baixa o segmento necessário)
    │
    ▼
ffmpeg (gera paleta de cores + converte para GIF)
    │
    ▼
Auto-ajuste se > 20MB (reduz FPS/resolução)
    │
    ▼
GIF pronto para download
```

---

## 📝 Limitações

- **Instagram/TikTok**: Funciona apenas para vídeos **públicos**. Perfis privados não funcionam.
- **YouTube**: Funciona para a maioria dos vídeos públicos.
- **Duração máxima recomendada**: 60 segundos (GIFs muito longos ficam grandes mesmo comprimidos).
- Os GIFs são deletados automaticamente do servidor após 10 minutos.

---

## 🔧 Problemas comuns

**"Não foi possível obter informações do vídeo"**
- Verifique se o vídeo é público
- Atualize o yt-dlp: `pip3 install --upgrade yt-dlp`

**"Servidor inacessível"**  
- Certifique-se de que o `start.sh` está rodando no terminal

**GIF ficou muito grande**  
- Reduza a largura para 320px
- Reduza o FPS para 8
- Encurte o trecho selecionado
