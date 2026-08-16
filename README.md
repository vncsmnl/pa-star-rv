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
Dashboard completo com cartões de KPIs e tabelas estruturadas:
- **Search Effort**: Total de expansões registradas, nós economizados ($N_A - N_B$) e redução percentual.
- **Unique States & Deduplicação**: Estados únicos em A e B, interseção de estados comuns, estados exclusivos (Only A / Only B) e diagnósticos de consistência interna de $h$ e $g$.
- **Heuristic Advantage**: Estatísticas de $\Delta h = h_B(s) - h_A(s)$ calculadas sobre estados comuns válidos.
- **Diagnostics**: Verificação $f(n) == g(n) + h(n)$ no log e consistência de custo de caminho ($g_A == g_B$).
- **Footprint Occupancy**: Células ocupadas e sobreposição de Jaccard nas projeções $XY$, $XZ$ e $YZ$.

### 2. Economia de Busca (`Search Savings`)
Análise da redução de esforço ao longo do **Progresso Geométrico de Alinhamento**:
- *Cumulative Expanded Nodes by Geometric Progress* (A vs B).
- *Cumulative Expansion Difference by Geometric Progress* ($cum_A - cum_B$).
- *Nodes Saved in Region* (Gráfico de barras: economia local por bin).
- *Local Expansion Reduction (%)* e *Local Expansion Ratio (B / A)* com mascaramento para bins sem suporte estatístico mínimo.

### 3. Cobertura do Espaço de Estados (`Search Footprint`)
Mapas de calor comparativos para as projeções ortogonais $XY$, $XZ$ e $YZ$:
- Pegada de A e B (escala logarítmica compartilhada).
- *Absolute Expansion Difference* ($H_B - H_A$) com mapa de cores divergente simétrico centrado em zero.
- *Relative Exploration Density Difference* ($H_{B,norm} - H_{A,norm}$).
- Tabela integrada de células ocupadas e coeficiente de Jaccard.

### 4. Comportamento Heurístico (`Heuristic Behaviour`)
Comparação detalhada das funções de avaliação ao longo do espaço geométrico:
- Perfis de $h(n)$, $g(n)$ e $f(n)$ por progresso geométrico (medianas e percentis P25/P75).
- Histograma de $\Delta h = h_B(s) - h_A(s)$ sobre estados comuns válidos.
- Dispersão $h_A \times h_B$ com linha de referência diagonal $y = x$.

### 5. Banda de Busca (`Search Band`)
Mede o desvio euclidiano dos estados expandidos em relação à diagonal principal (linha $i = j = k = \dots$):
- Perfil de largura de banda por progresso geométrico (P25, mediana, P75, P90 para A e B).
- Distribuições globais de desvio em contagem absoluta e densidade normalizada.

### 6. Densidade de Exploração (`Exploration Density`)
Mapas de calor individuais de frequência de expansão de nós na grade discreta com linha diagonal de referência.

### 7. Dinâmica de Expansão (`Expansion Dynamics`)
- Mínimo local de $h(n)$ de nós expandidos (*Local Minimum h(n)*).
- Média local de $h(n)$ de nós expandidos (*Local Average h(n)*).
- Distribuição de passos de deslocamento de expansão (*Expansion Displacement* em distância Manhattan).
- Deslocamentos acumulados ao longo do índice de expansão.

### 8. Trajetória 3D e Projeções (`3D + Projections`)
Visualização 3D interativa acelerada por OpenGL com gradiente de cor temporal e projeções 2D ortogonais sincronizadas.

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
