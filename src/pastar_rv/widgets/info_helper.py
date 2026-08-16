"""
Contextual Help & Info Badges (info_helper)
Provides rich interactive 'ℹ' info badges and comprehensive explanations
for all UI controls, tabs, metrics, and plots across the PA-Star Runtime Visualizer.
"""

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QCursor, QFont
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QWidget,
    )
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QCursor, QFont
    from PyQt5.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QWidget,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RICH HTML TOOLTIP TEMPLATES & DESCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────


def format_tooltip(
    title: str, description: str, interpretation: str = "", formula: str = ""
) -> str:
    """Formats a clean, modern HTML tooltip with title, description, and interpretation guide."""
    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; color: #1e293b; max-width: 380px; line-height: 1.45;">
        <div style="font-size: 13px; font-weight: bold; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin-bottom: 6px;">
            ℹ {title}
        </div>
        <div style="margin-bottom: 6px; color: #334155;">
            {description}
        </div>
    """
    if formula:
        html += f"""
        <div style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-family: Consolas, monospace; font-size: 11px; color: #0f172a; margin-bottom: 6px; border-left: 3px solid #0284c7;">
            <b>Fórmula / Conceito:</b> {formula}
        </div>
        """
    if interpretation:
        html += f"""
        <div style="background: #eff6ff; padding: 5px 8px; border-radius: 4px; font-size: 11px; color: #1e40af; border: 1px solid #bfdbfe;">
            <b>💡 Como interpretar:</b> {interpretation}
        </div>
        """
    html += "</div>"
    return html.strip()


# Comprehensive Tooltips Dictionary
TOOLTIPS = {
    # ── Top Bar Options ──
    "btn_open_a": format_tooltip(
        "Abrir Log A (Baseline)",
        "Carrega o arquivo de log da execução de referência (Baseline), por exemplo utilizando a heurística padrão (2all) ou execução sequencial/base.",
        "Este dataset será usado como base de comparação para calcular economia de nós, diferenças heurísticas e sobreposição espacial.",
    ),
    "btn_open_b": format_tooltip(
        "Abrir Log B (Candidato)",
        "Carrega o arquivo de log da execução candidata (otimizada ou variante), por exemplo utilizando heurística mais informada (3all), nova função hash ou arquitetura paralela.",
        "Os gráficos comparativos avaliarão o ganho ou custo de B em relação a A.",
    ),
    "btn_save_current": format_tooltip(
        "Salvar Imagem da Aba Atual",
        "Exporta uma captura em alta resolução (PNG) de todos os gráficos e tabelas presentes na aba visualizada no momento.",
        "Ideal para gerar figuras individuais para artigos, relatórios ou apresentações.",
    ),
    "btn_export_all": format_tooltip(
        "Exportar Todas as Abas",
        "Gera e salva automaticamente imagens PNG de todas as 8 abas analíticas em uma pasta selecionada.",
        "Facilita a documentação completa do experimento comparativo entre os logs A e B.",
    ),
    "switcher_single": format_tooltip(
        "Seletor de Arquivo Ativo (Abas Individuais)",
        "Alterna qual dos dois arquivos (A ou B) terá seus dados renderizados nas abas de visualização individual (Densidade de Exploração, Dinâmica de Expansão e Projeções do Espaço de Estados).",
        "Permite inspecionar em detalhes a dinâmica isolada de cada execução sem recarregar o arquivo.",
    ),
    # ── Tab Descriptions ──
    "tab_summary": format_tooltip(
        "Aba 1: Resumo Executivo (Summary)",
        "Painel consolidado com cartões de KPIs de alto nível e tabelas detalhadas de esforço de busca, deduplicação de estados, vantagem heurística e diagnósticos de consistência.",
        "Fornece uma visão geral rápida e rigorosa do impacto algorítmico entre as execuções A e B.",
    ),
    "tab_savings": format_tooltip(
        "Aba 2: Economia de Busca (Search Savings)",
        "Analisa a redução no número de expansões ao longo do Progresso Geométrico de Alinhamento (0% a 100%).",
        "Mostra em quais fases do alinhamento (início, meio ou fim) a heurística candidata economizou mais esforço computacional.",
    ),
    "tab_footprint": format_tooltip(
        "Aba 3: Cobertura do Espaço de Estados (Search Footprint)",
        "Projeta os estados expandidos em todas as combinações de pares de sequências 2D (matriz par-a-par) e calcula a sobreposição espacial de Jaccard.",
        "Identifica se a busca ficou mais focada na diagonal ou se explorou regiões laterais desnecessárias.",
    ),
    "tab_heuristic": format_tooltip(
        "Aba 4: Comportamento Heurístico (Heuristic Behaviour)",
        "Compara as curvas de h(n), g(n) e f(n) ao longo do progresso e avalia a diferença heurística (Δh = h_B − h_A) nos estados comuns.",
        "Valores de Δh > 0 comprovam maior informatividade e dominância da heurística candidata B.",
    ),
    "tab_band": format_tooltip(
        "Aba 5: Banda de Busca (Search Band)",
        "Mede a distância euclidiana dos estados expandidos em relação à diagonal principal (alinhamento ótimo teórico).",
        "Uma banda mais estreita indica busca mais direcionada e menor dispersão do espaço de busca.",
    ),
    "tab_density": format_tooltip(
        "Aba 6: Densidade de Exploração (Exploration Density)",
        "Mapas de calor 2D da densidade de expansões em escala logarítmica para quaisquer eixos de sequências selecionados.",
        "Regiões mais brilhantes indicam gargalos ou áreas de grande esforço de expansão no alinhamento.",
    ),
    "tab_dynamics": format_tooltip(
        "Aba 7: Dinâmica de Expansão (Expansion Dynamics)",
        "Analisa a evolução temporal do mínimo e média local de h(n), além do tamanho dos saltos espaciais (deslocamento Manhattan L1) entre expansões consecutivas.",
        "Quedas contínuas no mínimo de h(n) indicam avanço consistente rumo ao estado objetivo; saltos menores indicam localidade espacial.",
    ),
    "tab_classic": format_tooltip(
        "Aba 8: Projeções do Espaço de Estados (State Space Projections)",
        "Visualização tridimensional interativa via OpenGL e projeções 2D coloridas pela linha do tempo de iterações (início azul → fim vermelho).",
        "Permite inspecionar a nuvem completa de nós expandidos e sua trajetória no espaço euclidiano.",
    ),
    # ── Summary Tab KPIs & Groups ──
    "kpi_expansions_a": format_tooltip(
        "Expansões no Dataset A (Baseline)",
        "Número total de nós/estados expandidos registrados no arquivo de log A durante a execução do algoritmo.",
        "Valor de referência para medir a eficiência de busca.",
    ),
    "kpi_expansions_b": format_tooltip(
        "Expansões no Dataset B (Candidato)",
        "Número total de nós/estados expandidos registrados no arquivo de log B durante a execução do algoritmo.",
        "Comparado diretamente contra A para verificar redução de nós.",
    ),
    "kpi_nodes_saved": format_tooltip(
        "Total de Expansões Economizadas",
        "Diferença absoluta no número total de expansões entre o Baseline A e o Candidato B.",
        "Valores positivos (+ verde) indicam que B expandiu menos nós que A, economizando tempo e memória.",
        formula="N_A − N_B",
    ),
    "kpi_reduction_pct": format_tooltip(
        "Redução Percentual de Expansões",
        "Percentual relativo de nós que o Candidato B deixou de expandir em comparação ao Baseline A.",
        "Quanto maior a porcentagem positiva, maior o ganho de eficiência do algoritmo candidato.",
        formula="((N_A − N_B) / N_A) × 100%",
    ),
    "kpi_common_states": format_tooltip(
        "Estados Únicos Comuns",
        "Quantidade de coordenadas geométricas D-dimensionais exatas que foram visitadas tanto na execução A quanto na execução B.",
        "Permite realizar comparações pareadas estado-a-estado justas e rigorosas para cálculo de Δh e consistência de g.",
    ),
    "group_effort": format_tooltip(
        "1. Esforço de Busca & Deslocamento de Expansão",
        "Compara o volume total de expansões, saltos espaciais e largura média da banda de busca entre as execuções A e B.",
        "Avalia se a nova heurística reduziu o trabalho total e manteve o foco próximo à diagonal ótima.",
    ),
    "group_states": format_tooltip(
        "2. Estados Únicos Expandidos & Deduplicação",
        "Quantifica os estados espaciais únicos explorados por cada algoritmo e identifica quais foram evitados ou adicionados.",
        "'Only in A' são estados que a heurística candidata B conseguiu podar com sucesso.",
    ),
    "group_heur_adv": format_tooltip(
        "3. Vantagem Heurística em Estados Comuns (Δh = h_B − h_A)",
        "Estatísticas da diferença de estimativa heurística avaliada exatamente sobre os mesmos estados visitados por A e B.",
        "Se a maioria dos estados tiver Δh > 0 e a média for positiva, a heurística B é estritamente mais informada.",
        formula="Δh(s) = h_B(s) − h_A(s)",
    ),
    "group_diag": format_tooltip(
        "4. Diagnósticos de Consistência de Custo e Log",
        "Verifica a integridade matemática dos logs: validação da relação f == g + h e verificação se o custo acumulado g(s) até estados comuns foi idêntico.",
        "Taxa de 100% de match em g indica concordância no custo ótimo dos caminhos explorados.",
    ),
    "group_footprint": format_tooltip(
        "5. Ocupação do Espaço 2D & Sobreposição de Jaccard",
        "Mede a sobreposição das células espaciais ocupadas nas projeções 2D entre os alinhamentos.",
        "O índice de Jaccard varia de 0.0 (sem sobreposição) a 1.0 (cobertura idêntica).",
        formula="Jaccard = |A ∩ B| / |A ∪ B|",
    ),
    # ── Search Savings Plots ──
    "plot_cum_exp": format_tooltip(
        "Expansões Acumuladas por Progresso Geométrico",
        "Exibe o número cumulativo de nós expandidos conforme o alinhamento avança do início (0.0) até o objetivo (1.0).",
        "A curva que estiver mais abaixo no gráfico realizou menos expansões até aquele ponto do progresso (linha azul = A, linha vermelha = B).",
    ),
    "plot_cum_diff": format_tooltip(
        "Diferença Acumulada de Expansões (A − B)",
        "Mostra a economia total acumulada de expansões gerada pelo Candidato B em relação a A ao longo do progresso.",
        "Curva acima de 0 (verde) = B economizou nós. Inclinação positiva = B está ganhando vantagem nesse trecho; inclinação negativa = B está expandindo mais que A nesse trecho.",
        formula="cum_diff(p) = cum_A(p) − cum_B(p)",
    ),
    "plot_local_saved": format_tooltip(
        "Nós Economizados na Região Local",
        "Gráfico de barras indicando a quantidade de nós economizados em cada intervalo (bin) de progresso geométrico.",
        "Barras verdes para cima = B expandiu menos nós no intervalo. Barras vermelhas para baixo = B expandiu mais nós no intervalo.",
    ),
    "plot_local_red": format_tooltip(
        "Redução Percentual Local (%)",
        "Percentual relativo de redução de nós em cada bin de progresso, filtrado por suporte estatístico mínimo.",
        "Valores próximos de 100% indicam poda quase total do espaço de busca naquela região específica do alinhamento.",
    ),
    "plot_local_ratio": format_tooltip(
        "Razão de Expansão Local (B / A)",
        "Relação entre o número de nós expandidos por B e por A em cada região do alinhamento.",
        "Linha tracejada vermelha em 1.0 representa esforço igual. Valores < 1.0 (abaixo da linha) indicam que B foi mais eficiente.",
        formula="ratio(p) = local_B(p) / local_A(p)",
    ),
    # ── Search Footprint Plots & Controls ──
    "footprint_table": format_tooltip(
        "Tabela de Projeções Par-a-Par e Jaccard",
        "Lista todas as combinações de pares de sequências D-dimensionais, comparando células 2D ocupadas por A, por B, compartilhadas e exclusivas.",
        "Dê um clique duplo ou selecione uma linha para abrir a análise detalhada com 4 mapas de calor daquele par de sequências.",
    ),
    "matrix_view": format_tooltip(
        "Matriz de Projeções Par-a-Par (Scatter-Matrix)",
        "Matriz triangular superior com todos os D*(D-1)/2 pares de projeção. Exibe a Diferença Absoluta de Expansão em mapa RdBu.",
        "Azul = Baseline A expandiu mais nessa região; Vermelho = Candidato B expandiu mais; Branco = expansão equivalente.",
    ),
    "detail_pair_selector": format_tooltip(
        "Seletor de Par de Sequências",
        "Escolha qual par de sequências (e.g. Seq 1 vs Seq 2) será detalhado nos 4 mapas de calor em alta resolução.",
        "Permite inspecionar a topologia da exploração entre duas sequências específicas do alinhamento múltiplo.",
    ),
    "plot_detail_a": format_tooltip(
        "Mapa de Calor de Expansão: Dataset A (Log Count)",
        "Distribuição espacial 2D das expansões no Dataset A em escala logarítmica log(1 + count).",
        "Cores mais quentes (amarelo/laranja) indicam regiões com altíssima concentração de expansões em A.",
    ),
    "plot_detail_b": format_tooltip(
        "Mapa de Calor de Expansão: Dataset B (Log Count)",
        "Distribuição espacial 2D das expansões no Dataset B em escala logarítmica log(1 + count).",
        "Compare diretamente com o gráfico de A para ver onde a busca de B foi mais enxuta ou canalizada.",
    ),
    "plot_detail_diff_abs": format_tooltip(
        "Diferença Absoluta de Expansão (A − B)",
        "Diferença direta na contagem de expansões em cada célula do grid 2D usando colormap divergente RdBu.",
        "Azul = A realizou mais expansões (B economizou aqui); Vermelho = B realizou mais expansões; Branco = contagens iguais.",
        formula="diff_abs = Count_B(x, y) − Count_A(x, y)",
    ),
    "plot_detail_diff_rel": format_tooltip(
        "Diferença de Densidade Relativa (Normalizada)",
        "Diferença entre as probabilidades normalizadas de visitação espacial P(x, y), desacoplada do número total de nós.",
        "Destaca mudanças estruturais no foco da busca, independente de B ter menos nós globais que A.",
        formula="diff_rel = (Count_B / Total_B) − (Count_A / Total_A)",
    ),
    # ── Heuristic Behaviour Plots ──
    "plot_h_profile": format_tooltip(
        "Perfil Heurístico h(n) por Progresso",
        "Evolução do valor heurístico h(n) ao longo do progresso geométrico (mediana e intervalo interquartil P25–P75).",
        "No início do alinhamento (progresso 0.0), quanto maior o valor de h(n), mais informada e próxima da distância real é a heurística.",
    ),
    "plot_g_profile": format_tooltip(
        "Perfil de Custo de Caminho g(n) por Progresso",
        "Evolução do custo acumulado de caminho g(n) ao longo do progresso geométrico.",
        "Curvas crescentes representam o acúmulo de substituições e inserções/deleções (gaps) no alinhamento.",
    ),
    "plot_f_profile": format_tooltip(
        "Perfil da Função de Avaliação f(n) = g(n) + h(n)",
        "Comportamento da estimativa total f(n) que guia a fila de prioridades do algoritmo A*.",
        "Uma função f consistente e bem calibrada permanece estável ao longo de todo o progresso.",
    ),
    "plot_dh_hist": format_tooltip(
        "Histograma de Δh em Estados Comuns Válidos",
        "Distribuição da diferença de estimativa heurística Δh = h_B(s) − h_A(s) calculada exclusivamente para estados idênticos visitados por ambos.",
        "Valores à direita da linha tracejada vermelha (Δh > 0) comprovam empiricamente que B fornece estimativas mais rigorosas que A.",
        formula="Δh(s) = h_B(s) − h_A(s)",
    ),
    "plot_scatter_h": format_tooltip(
        "Dispersão h_A × h_B em Estados Comuns",
        "Gráfico de dispersão pareada comparando o valor heurístico de cada estado comum em A (eixo X) vs B (eixo Y).",
        "Pontos acima da linha diagonal vermelha (y = x) representam estados onde o Candidato B foi estritamente superior a A.",
        formula="Referência: y = x (h_B == h_A)",
    ),
    # ── Search Band Plots ──
    "plot_band_profile": format_tooltip(
        "Largura da Banda de Busca por Progresso",
        "Desvio euclidiano dos estados expandidos em relação à diagonal principal (0,0... → L1,L2...) ao longo do progresso.",
        "Faixa mais estreita (menor mediana e P90) comprova que o algoritmo não se afastou desnecessariamente do alinhamento ideal.",
    ),
    "plot_band_dist_abs": format_tooltip(
        "Distribuição de Desvio da Banda (Contagem Absoluta)",
        "Histograma da quantidade bruta de nós expandidos em função da distância à diagonal.",
        "Permite ver se A (azul) explorou muito mais nós em desvios elevados do que B (vermelho).",
    ),
    "plot_band_dist_density": format_tooltip(
        "Distribuição de Desvio da Banda (Densidade Normalizada)",
        "Função densidade de probabilidade do desvio da diagonal para cada algoritmo.",
        "Compara a concentração do formato da busca de forma justa, normalizando a diferença no total de nós.",
    ),
    # ── Exploration Density Controls & Plots ──
    "density_controls": format_tooltip(
        "Controles de Projeção da Densidade",
        "Permite selecionar livremente quais duas sequências do problema D-dimensional serão projetadas nos eixos X e Y do mapa de calor.",
        "Alterne os seletores para inspecionar gargalos entre pares específicos de sequências.",
    ),
    "plot_density_main": format_tooltip(
        "Densidade de Exploração da Projeção Selecionada",
        "Mapa de calor 2D da contagem de nós em escala logarítmica com linha diagonal de alinhamento perfeito (vermelho tracejado).",
        "Nós concentrados ao redor da linha diagonal indicam alinhamento de alta fidelidade e baixo número de gaps.",
    ),
    # ── Expansion Dynamics Plots ──
    "plot_dyn_min_h": format_tooltip(
        "Mínimo Local de h(n) ao Longo das Expansões",
        "Menor valor de h(n) observado em uma janela móvel de expansões consecutivas.",
        "Curva monotonicamente decrescente indica que o algoritmo está avançando de forma direta e sem estagnação em mínimos locais.",
    ),
    "plot_dyn_avg_h": format_tooltip(
        "Média Local de h(n) ao Longo das Expansões",
        "Valor médio de h(n) em janela móvel durante a busca.",
        "Oscilações bruscas indicam que a busca está alternando entre diferentes ramos ou bacias de atração do espaço de estados.",
    ),
    "plot_dyn_jdist": format_tooltip(
        "Distribuição de Saltos de Expansão (Manhattan L1)",
        "Histograma da distância Manhattan |coord_t − coord_{t-1}|_1 entre nós expandidos consecutivamente no log.",
        "Saltos pequenos (distância = 1 a 3) indicam expansões contíguas e alta localidade espacial. Saltos grandes indicam troca frequente de threads/ramos.",
        formula="dist_L1 = Σ |x_{t, i} − x_{t-1, i}|",
    ),
    "plot_dyn_cumj": format_tooltip(
        "Deslocamentos Espaciais Acumulados",
        "Contagem acumulada de saltos/deslocamentos espaciais significativos ao longo do índice normalizado de expansões.",
        "Inclinação mais suave (curva mais baixa) indica sequência de expansão mais focada e com menos dispersão de memória.",
    ),
    # ── State Space 3D Projections ──
    "banner_3d": format_tooltip(
        "Modo de Espaço de Estados (3D)",
        "Informa se a visualização 3D representa o espaço de estados completo (quando D = 3 sequências) ou uma projeção parcial (quando D > 3).",
        "Em alinhamentos com D > 3, use os seletores de eixos para explorar diferentes trios de sequências.",
    ),
    "ctrl_3d_axes": format_tooltip(
        "Seletores de Eixos 3D (X, Y, Z)",
        "Escolha quais 3 sequências do alinhamento serão mapeadas nos eixos tridimensionais da visualização OpenGL.",
        "Permite inspecionar a nuvem de pontos tridimensional sob qualquer perspectiva de trios de sequências.",
    ),
    "ctrl_2d_axes": format_tooltip(
        "Seletores de Eixos 2D (X, Y)",
        "Escolha quais 2 sequências serão exibidas no gráfico de dispersão 2D com gradiente de cores temporal.",
        "Cores acompanham a linha do tempo: azul (primeiras iterações) → verde/amarelo → vermelho (iterações finais).",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
#  INFO BADGE WIDGET
# ─────────────────────────────────────────────────────────────────────────────


class InfoBadge(QLabel):
    """
    Modern, sleek circular 'ℹ' badge widget with custom hover effect
    and rich HTML tooltip integration.
    """

    def __init__(self, tooltip_key_or_html: str, parent=None):
        super().__init__("ℹ", parent)
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(18, 18)

        # Style with clean blue badge aesthetic and subtle hover transition
        self.setStyleSheet(
            "QLabel {"
            "  background-color: #e0f2fe;"
            "  color: #0369a1;"
            "  border: 1px solid #bae6fd;"
            "  border-radius: 9px;"
            "  font-weight: bold;"
            "  font-size: 11px;"
            "}"
            "QLabel:hover {"
            "  background-color: #0284c7;"
            "  color: #ffffff;"
            "  border: 1px solid #0369a1;"
            "}"
        )

        # Set tooltip from dictionary key or direct HTML string
        content = TOOLTIPS.get(tooltip_key_or_html, tooltip_key_or_html)
        self.setToolTip(content)


def create_info_badge(tooltip_key_or_html: str) -> InfoBadge:
    """Helper to instantiate an InfoBadge."""
    return InfoBadge(tooltip_key_or_html)


def wrap_with_info(widget: QWidget, tooltip_key_or_html: str) -> QWidget:
    """Wraps a label or title widget horizontally with an adjacent InfoBadge."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(widget)
    badge = InfoBadge(tooltip_key_or_html)
    layout.addWidget(badge)
    return container
