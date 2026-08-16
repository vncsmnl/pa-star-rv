# PA-Star Runtime Visualizer (`pastar-rv`)

Ferramenta de análise visual e quantitativa em tempo de execução para avaliação e comparação rigorosa do comportamento do algoritmo **PA-Star** (Parallel A*) no problema de **Alinhamento Múltiplo de Sequências (MSA)**.

*Read this in other languages:* [English](README_EN.md)

---

## Visão Geral

O `pastar-rv` permite investigar a dinâmica de exploração espacial e heurística gerada durante a execução do PA-Star (e.g. comparando heurísticas como `2all` vs `3all` ou variações de paralelismo e hash).

A ferramenta é projetada para processar eficientemente logs com milhões de nós através de rotinas puras NumPy vetorizadas, separando a camada de análise matemática exata do *downsampling* estritamente visual.

---

## Módulos de Visualização

A aplicação é estruturada em oito abas analíticas:

### 1. Resumo Executivo (`Summary`)

![Resumo Executivo](assets/1fjlA_2all_vs_1fjlA_3all__summary.png)

Dashboard completo com cartões de KPIs e tabelas estruturadas:
- **Search Effort**: Total de expansões registradas, nós economizados ($N_A - N_B$) e redução percentual.
- **Unique States & Deduplicação**: Estados únicos em A e B, interseção de estados comuns, estados exclusivos (Only A / Only B) e diagnósticos de consistência interna de $h$ e $g$.
- **Heuristic Advantage**: Estatísticas de $\Delta h = h_B(s) - h_A(s)$ calculadas sobre estados comuns válidos.
- **Diagnostics**: Verificação $f(n) == g(n) + h(n)$ no log e consistência de custo de caminho ($g_A == g_B$).
- **Footprint Occupancy**: Células ocupadas e sobreposição de Jaccard nas projeções $XY$, $XZ$ e $YZ$.

### 2. Economia de Busca (`Search Savings`)

![Economia de Busca](assets/1fjlA_2all_vs_1fjlA_3all__savings.png)

Análise da redução de esforço ao longo do **Progresso Geométrico de Alinhamento**:
- *Cumulative Expanded Nodes by Geometric Progress* (A vs B).
- *Cumulative Expansion Difference by Geometric Progress* ($cum_A - cum_B$).
- *Nodes Saved in Region* (Gráfico de barras: economia local por bin).
- *Local Expansion Reduction (%)* e *Local Expansion Ratio (B / A)* com mascaramento para bins sem suporte estatístico mínimo.

### 3. Cobertura do Espaço de Estados (`Search Footprint`)

![Cobertura do Espaço de Estados](assets/1fjlA_2all_vs_1fjlA_3all__footprint.png)

Análise generalizada para todas as $\binom{D}{2}$ projeções pairwise com matriz de dispersão:
- **Pairwise Projections Matrix**: Matriz triangular superior exibindo a diferença absoluta de expansão (*Absolute Expansion Difference*) para todas as relações de pares (e.g. 15 pares para $D=6$).
- **Visualização Detalhada de Pares**: Seletor interativo com 4 mapas de calor em alta resolução (A, B, Diferença Absoluta com mapa RdBu simétrico centrado em zero e Densidade Relativa).
- Tabela dinâmica de células ocupadas e sobreposição de Jaccard para todos os pares.

### 4. Comportamento Heurístico (`Heuristic Behaviour`)

![Comportamento Heurístico](assets/1fjlA_2all_vs_1fjlA_3all__heuristic.png)

Comparação detalhada das funções de avaliação ao longo do espaço geométrico $D$-dimensional:
- Perfis de $h(n)$, $g(n)$ e $f(n)$ por progresso geométrico (medianas e percentis P25/P75).
- Histograma de $\Delta h = h_B(s) - h_A(s)$ sobre estados comuns válidos calculados no espaço $D$-dimensional original.
- Dispersão $h_A \times h_B$ com linha de referência diagonal $y = x$.

### 5. Banda de Busca (`Search Band`)

![Banda de Busca](assets/1fjlA_2all_vs_1fjlA_3all__band.png)

Mede o desvio euclidiano dos estados expandidos em relação à diagonal principal ($i = j = k = \dots$) no espaço $D$-dimensional:
- Perfil de largura de banda por progresso geométrico (P25, mediana, P75, P90 para A e B).
- Distribuições globais de desvio em contagem absoluta e densidade normalizada.

### 6. Densidade de Exploração (`Exploration Density`)

![Densidade de Exploração](assets/1fjlA_2all_vs_1fjlA_3all__density.png)

Mapas de calor de densidade de exploração com seletores de dimensões ($X: S_i, Y: S_j$) e linha diagonal de referência para qualquer projeção do espaço $D$-dimensional.

### 7. Dinâmica de Expansão (`Expansion Dynamics`)

![Dinâmica de Expansão](assets/1fjlA_2all_vs_1fjlA_3all__dynamics.png)

- Mínimo local de $h(n)$ de nós expandidos (*Local Minimum h(n)*).
- Média local de $h(n)$ de nós expandidos (*Local Average h(n)*).
- Distribuição de passos de deslocamento de expansão (*Expansion Displacement* em distância Manhattan).
- Deslocamentos acumulados ao longo do índice de expansão.

### 8. Projeções no Espaço de Estados (`State Space Projections`)

![Projeções no Espaço de Estados](assets/1fjlA_2all_vs_1fjlA_3all__classic.png)

Visualizador adaptativo acelerado por OpenGL:
- **$D = 3$**: Habilita 3D completo com badge indicativo de que $(x, y, z)$ representa o estado inteiro sem perda de informação.
- **$D > 3$**: Exibe banner de aviso explícito indicando projeção 3D parcial ($S_i \times S_j \times S_k$ apenas), alertando que o gráfico não deve ser usado como evidência global do espaço de busca.
- **Seletores de Dimensões**: Seletores dinâmicos para eixos 3D e eixos 2D ($X: S_i, Y: S_j$), permitindo inspecionar qualquer uma das $\binom{D}{2}$ projeções bidimensionais com gradiente de tempo de iteração e linha diagonal.

---

## Validação e Benchmark via CLI (`pastar-validate`)

O pacote inclui uma ferramenta de linha de comando para validação matemática e benchmarking sem necessidade de abrir a interface gráfica:

```bash
uv run pastar-validate logs/1fjlA_2all.txt logs/1fjlA_3all.txt
```

O script reporta:
- Tempo de execução e pico de memória do processo (RSS).
- Benchmarking das estratégias de interseção de estados.
- Relatório quantitativo completo de esforço de busca, estados únicos, $\Delta h$, ocupação e diagnósticos.

---

## Conceitos e Terminologia

| Conceito | Definição Rigorosa |
| :--- | :--- |
| **Expansion Count** | Quantidade total de nós/entradas registradas no log de execução. |
| **Unique Expanded States** | Quantidade de coordenadas distintas exploradas no espaço de estados. |
| **Occupied Cells** | Quantidade de bins ocupados em uma projeção 2D (não é sinônimo de estados explorados). |
| **Progresso Geométrico de Alinhamento** | Projeção normalizada do estado no espaço de alinhamento $\frac{1}{D}\sum \frac{\text{coord}_d}{\text{ref}_d}$, não representando tempo ou profundidade. |
| **$\Delta h$ nos Estados Comuns** | Diferença $h_B(s) - h_A(s)$ calculada apenas em coordenadas exatas presentes e consistentes em ambas as execuções. |

---

## Estrutura do Projeto

```text
pa-star-rv/
├── pyproject.toml              # Configuração uv, dependências, ruff e scripts
├── uv.lock                     # Lockfile determinístico uv
├── src/
│   └── pastar_rv/             # Pacote principal
│       ├── __init__.py
│       ├── __main__.py        # Executável via python -m pastar_rv
│       ├── app.py             # Aplicação GUI principal (MainWindow)
│       ├── parser.py          # Parser vetorizado de logs
│       ├── metrics.py         # Módulo puro de análise estatística e métricas
│       ├── cli.py             # Ferramenta CLI de validação e benchmark
│       └── widgets/           # Canvases PyQtGraph / OpenGL
│           ├── __init__.py
│           ├── canvas_3d.py
│           ├── canvas_band.py
│           ├── canvas_density.py
│           ├── canvas_dynamics.py
│           ├── canvas_footprint.py
│           ├── canvas_heuristic.py
│           ├── canvas_savings.py
│           └── canvas_summary.py
├── tests/                     # Suíte de testes unitários e de integração
│   ├── __init__.py
│   ├── test_metrics.py        # Testes de unidade do módulo metrics
│   └── test_gui_integration.py# Testes de integração dos widgets e MainWindow
├── assets/                    # Capturas de tela e figuras de demonstração
└── logs/                      # Logs de exemplo de execução
```

---

## Requisitos e Instalação

### Pré-requisitos
* Python 3.10+
* [uv](https://docs.astral.sh/uv/)

### Instalação
```bash
uv sync
```

---

## Como Executar

### Interface Gráfica
```bash
uv run pastar-rv
```

1. Clique em **"📂 Open Log A (Baseline)"** para carregar o log de execução principal (e.g. `2all`).
2. Clique em **"📂 Open Log B (Candidate)"** para carregar o log secundário (e.g. `3all`).
3. Navegue pelas abas analíticas (**Summary**, **Search Savings**, **Search Footprint**, **Heuristic Behaviour**, etc.).
4. Utilize os botões **"💾 Save Current Tab"** ou **"💾 Export All Tabs"** para exportar as figuras em alta resolução.

### Testes Automatizados
```bash
uv run pytest
```

### Qualidade de Código (Lint & Format)
```bash
ruff check .
ruff format --check .
```
