web: sh -c "sed -i 's/\.filters{position:sticky;top:0;z-index:2}/.filters{position:relative;z-index:1}/' static/index.html && exec waitress-serve --listen=0.0.0.0:$PORT app:app"
