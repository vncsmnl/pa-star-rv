# PA-Star Runtime Visualizer (`pa-star-rv`)

Ferramenta de análise visual e quantitativa em tempo de execução para avaliação do comportamento do algoritmo **PA-Star** (Parallel A*) no problema de **Alinhamento Múltiplo de Sequências (MSA)**.

*Read this in other languages:* [English](README_EN.md)


## Visão Geral

O `pa-star-rv` permite investigar a dinâmica de exploração no espaço de estados 3D gerada durante a execução paralela do PA-Star. A ferramenta consome logs de execução e fornece métricas quantitativas de desempenho, desvio da diagonal principal, padrão de saltos de threads e evolução das funções de custo $f(n) = g(n) + h(n)$.

---

## Módulos de Visualização

O sistema é estruturado em seis módulos analíticos interativos:

### 1. Trajetória 3D e Projeções (`classic`)
Exibe a trajetória tridimensional da busca A* no espaço de alinhamento com mapeamento de cores temporal por iteração e projeções ortogonais nos planos $XY$, $XZ$ e $YZ$.

![Trajetória 3D e Projeções](assets/actin_2all_vs_actin_3all__classic.png)

### 2. Densidade de Exploração (`density`)
Mapa de calor da frequência de expansão de nós na grade discreta, permitindo identificar regiões de alta convergência e estagnação da busca.

![Densidade de Exploração](assets/actin_2all_vs_actin_3all__density.png)

### 3. Dinâmica de Busca (`dynamics`)
Evolução temporal das funções de custo g-score $g(n)$, h-score $h(n)$ e f-score $f(n)$, juntamente com métricas de saltos por iteração.

![Dinâmica de Busca](assets/actin_2all_vs_actin_3all__dynamics.png)

### 4. Desvio da Diagonal (`band`)
Mede o desvio euclidiano dos estados expandidos em relação à diagonal principal (linha $i = j = k$), essencial para avaliar a eficácia de heurísticas de estreitamento de banda (Search Band).

![Desvio da Diagonal](assets/actin_2all_vs_actin_3all__band.png)

### 5. Cobertura do Espaço de Estados (`footprint`)
Representação da amplitude espacial (footprint) e limites geométricos atingidos pela busca no espaço 3D.

![Pegada do Espaço de Estados](assets/actin_2all_vs_actin_3all__footprint.png)

### 6. Análise Comparativa (`compare`)
Permite carregar simultaneamente dois logs de execução (Log A e Log B) para comparar o impacto de variações de threads, partições de hash e parâmetros de *shift*.

![Análise Comparativa](assets/actin_2all_vs_actin_3all__compare.png)

---

## Métricas Calculadas

| Métrica | Descrição Acadêmica / Computacional |
| :--- | :--- |
| **Iterações ($N$)** | Quantidade total de expansões de nós no espaço de estados. |
| **Saltos de Thread (Jumps)** | Descontinuidades espaciais no espaço de busca causadas pela troca de contexto entre threads ou partições de hash (distância Manhattan $> 1$). |
| **Desvio de Banda ($\text{Dev}$)** | Distância euclidiana perpendicular entre as coordenadas do nó $(x, y, z)$ e a diagonal principal do alinhamento. |
| **Funções de Custo ($g, h, f$)** | Custo acumulado $g(n)$, estimativa heurística $h(n)$ e custo total $f(n) = g(n) + h(n)$ ao longo das iterações. |

---

## Formato do Log de Entrada

A ferramenta lê arquivos `.txt` gerados pelo PA-Star contendo o seguinte cabeçalho e estrutura tabulada:

```text
PA-Star Execution Log
Threads: 4
Hash: Full-Zorder
Shift: 12

0	1	Adding:	(1 0 0)	g(90) h(6913) f(7003)
0	2	Adding:	(0 1 0)	g(90) h(6913) f(7003)
...
```

---

## Estrutura do Projeto

```text
pa-star-rv/
├── pa-star-rv.py          # Aplicação principal (GUI em PyQt6)
├── parser.py              # Parser vetorizado de logs de alta performance (NumPy)
├── widgets/               # Módulos gráficos PyQtGraph / Matplotlib
│   ├── canvas_3d.py       # Trajetória 3D e projeções
│   ├── canvas_density.py  # Densidade de exploração
│   ├── canvas_dynamics.py # Dinâmica f, g, h
│   ├── canvas_band.py     # Desvio de banda diagonal
│   ├── canvas_footprint.py# Cobertura de estados (footprint)
│   └── canvas_comparison.py# Comparativo entre dois logs (A vs B)
├── assets/                # Capturas de tela e figuras de demonstração
├── logs/                  # Logs de exemplo de execução
└── requirements.txt       # Dependências Python
```

---

## Requisitos e Instalação

### Pré-requisitos
* Python 3.8+

### Instalação
```bash
pip install -r requirements.txt
```

Dependências principais:
* `PyQt6` / `PyQt5` — Interface gráfica com suporte a aceleração OpenGL.
* `pyqtgraph` — Renderização gráfica 2D/3D de alto desempenho.
* `matplotlib` — Renderização de mapas e projeções.
* `numpy` — Processamento vetorizado de dados em C.

---

## Como Executar

Inicie a interface gráfica executando:

```bash
python pa-star-rv.py
```

1. Clique em **"📂 Open Log A"** para carregar o log de execução principal.
2. (Opcional) Clique em **"📂 Open Log B"** para carregar um log secundário para análise comparativa.
3. Navegue pelas abas da interface para inspecionar cada dimensão da busca.
4. Utilize os botões **"💾 Save Current Tab"** ou **"💾 Export All Tabs"** para exportar as figuras em alta resolução.
