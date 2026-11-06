# NeuroBasket

Simulador 2D lateral de basquete com física própria e treinamento evolutivo de IA.

## Requisitos
- Python 3.12+
- pygame-ce 2.5.8 (compatível com o import pygame)

## Instalação (Windows / PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m neurobasket.main
```

O pygame-ce fornece wheels para Python 3.12+ no Windows; o ambiente foi validado com Python 3.14.

## Controles
- Clique e arraste a partir da bola para mirar.
- Solte o botão do mouse para arremessar.
- `R`: reiniciar a tentativa.
- Segure `Shift` para carregar força extra por até 1,5 segundo; o impulso é aplicado ao soltar o arremesso.
- `F11`: alternar entre janela e tela cheia.
- `ESC`: sair.

## Treinamento da IA

Com o ambiente virtual ativado, execute no terminal do VS Code:

```powershell
python -m neurobasket.training
```

O treinamento usa uma população padrão de 50 redes MLP (5 entradas, 8 neurônios
ocultos e 3 saídas) por 100 gerações. Cada rede escolhe o ângulo, a velocidade
do arremesso e uma força extra que aprende a dosar; a física do jogo mede o
resultado. Cada quicada no aro vale um ponto inicial e mais dois pontos por
quicada adicional; cestas na tabela valem dois e cestas limpas valem três.
A pontuação por quicadas continua ativa nas partidas. No treino, cestas de um
ponto recebem 34 de fitness, cestas de tabela recebem 68 e cestas limpas de
três pontos recebem 103. Quicadas adicionais não aumentam a recompensa de
treino. A evolução usa seleção, cruzamento e mutação.
Cada rede é avaliada em 16 fases fixas do movimento para favorecer consistência.
Quando o melhor resultado fica estagnado, o treino aumenta a mutação e injeta
novas redes na população. Os indivíduos mais fracos são substituídos a cada
geração, preservando os melhores. A IA recebe também a direção e a velocidade
da cesta, que se move em uma elipse estreita.

O fitness médio pode oscilar porque mede toda a população; o recorde histórico
do melhor indivíduo é preservado e não deve cair durante a mesma execução. O
intervalo visual entre gerações não altera a evolução.

Os limites configurados são 10.000 gerações e 5.000 indivíduos por geração.
Você pode aumentá-los editando `MAX_GENERATIONS` e `MAX_POPULATION` no início
de `neurobasket/training.py`. Os valores padrão também ficam ali como
`DEFAULT_GENERATIONS`, `DEFAULT_POPULATION` e `DEFAULT_GENERATION_DELAY_MS`.

Use o botão `Disputar com melhor bot` no painel para pausar o treino e jogar
contra a melhor rede encontrada até aquela geração. Os turnos alternam um
arremesso por vez; cestas usam as mesmas recompensas do treinamento, e vence
quem chegar primeiro a 10 pontos. Ao sair da partida, o treinamento continua.
Em cada arremesso humano, aparece um atleta sorteado entre LeBron James,
Stephen Curry, Jason Tatum, Gui Santos, Nikola Jokic, Viktor Wembanyama e Luka
Doncic; o sorteio evita repetir o atleta do arremesso humano anterior. O bot usa
sempre o mesmo boneco de robô genérico.

O painel mostra o melhor arremesso e sobrepõe as trajetórias da população da
geração atual, junto com métricas de cestas e fitness. Feche a janela ou pressione
`ESC` para encerrar o treino. Os arquivos `best_brain.json` e
`training_history.csv` são gravados em uma nova pasta `training_runs/run_.../`,
preservando os resultados de execuções anteriores. Para ajustar a
população e o número de gerações:

```powershell
python -m neurobasket.training --population 20 --generations 10
```

Para escolher os parâmetros na linha de comando, passe `--generations` e
`--population`. Por exemplo, para usar 1.000 gerações com 500 indivíduos por
geração:

```powershell
python -m neurobasket.training --generations 1000 --population 500 --generation-delay 1000
```

O treino realiza 16 avaliações por indivíduo em cada geração, então valores
maiores aumentam bastante o tempo de execução. Para treinar sem abrir a janela,
adicione `--headless`. Por padrão, o painel mantém cada geração visível por 500 ms; use
`--generation-delay 1000` para exibir cada uma por 1 segundo.

A direção do arrasto define a direção do lançamento. Quanto maior o arrasto,
maior a velocidade inicial, limitada para manter a simulação controlável.

## Estrutura

```text
NeuroBasket/
├── neurobasket/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── physics.py
│   ├── match.py
│   ├── simulation.py
│   ├── training_view.py
│   └── training.py
├── requirements.txt
└── README.md
```


