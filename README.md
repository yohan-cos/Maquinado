# Maquinado

Script de automação de movimentação sequencial para o jogo **pxgme.exe**.  
Executa alternância de teclas WASD de forma automática e controlada.

---

## Requisitos

- Windows 10 ou superior
- [Python 3.8+](https://www.python.org/downloads/) — durante a instalação, marque **"Add Python to PATH"** (caixa no rodapé do instalador)

---

## Instalação

1. Extraia a pasta `Maquinado` em qualquer local do seu computador
2. Abra a pasta e execute **`instalar.bat`** com duplo clique
3. Aguarde a instalação das dependências

Só precisa ser feito uma vez.

---

## Como usar

### 1. Inicie o script

Execute **`iniciar.bat`** — uma janela de confirmação de administrador aparecerá.  
Aceite. A interface do Maquinado abrirá automaticamente.

> O script precisa de permissão de administrador para interceptar teclas globalmente.

### 2. Entre no jogo

Abra o **pxgme.exe** normalmente.

### 3. Ative o modo script

Com o jogo em foco, pressione o **scroll do mouse (botão do meio)**.  
O indicador no topo da interface ficará **verde**: script ativado.

### 4. Acione a sequência

Pressione a tecla correspondente à direção desejada:

| Tecla | Sequência |
|-------|-----------|
| `W`   | Cima → Baixo |
| `S`   | Baixo → Cima |
| `D`   | Direita → Esquerda |
| `A`   | Esquerda → Direita |

A tecla acende na interface e o log registra cada movimento.

### 5. Interrompa quando quiser

| Ação | Resultado |
|------|-----------|
| Pressionar **qualquer outra tecla** | Para o loop, script continua ativo |
| Pressionar **WASD** | Inicia uma nova sequência imediatamente |
| **Scroll click** | Desativa o script completamente (WASD volta ao normal) |

---

## Interface

```
● Ativado  (scroll click para desativar)   ← estado global

● Rodando                                  ← estado do loop
    [W]
[A] [S] [D]                                ← tecla ativa acende em azul
Direita → Esquerda                         ← modo atual

Log
  ▶ Direita → Esquerda
    → D
    → A
    → D
```

---

## Observações

- O script **só age** quando o `pxgme.exe` está em foco
- A janela do Maquinado fica sempre visível sobre o jogo
- O jogo deve rodar em modo **janela** ou **borderless** para a sobreposição funcionar
