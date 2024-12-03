# -*- coding: utf-8 -*-

#%% Introduction
'''
The ambition of this script is to be able to take any input for which a volcano plot makes some sense (differential expression, splicing, proteomics etc.) and make volcano plots.
In practice, this script has access to several (37 by last count) dataframes generated by our lab and can scan them all for any gene or set of genes.
For the sake of protecting the intellectual property of the lab: ask Kasper for the input dataframes.
'''

#%% Initialization ============================================================
import pandas as pd
import math
from adjustText import adjust_text # Used to label data points without overlap
import os
from KTC_functions import KTC_GetGeneSet
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

#%% Settings =================================================

# =============================================================================
# Input and Output
# =============================================================================

in_dir       = '/Volumes/cmgg_pnlab/Kasper/Data/Interesting_Lists' # Directory where all "Interesting lists" are located
out_dir      = r'/Users/kasperthorhaugechristensen/Desktop/Dumpbox2/' #Directory where plots are saved
path_pdf     = os.path.join(out_dir, 'InterestingLists.pdf') #Name of pdf file produced. Output directory is 

# =============================================================================
# Defining a list of genes
# =============================================================================
# genes_of_interest is a list of the gene names as strings that will be searched.
# You can either:
#    1) Define your own custom list of gene names here in custom_list (use_custom_list=True))
#    2) Use KTC_GetGeneSet from KTC_functions.py to fetch a pre-defined list of genes (use_custom_list=False)
use_custom_list = False
custom_list = ['PRPF8', 'SRRM1', 'SRRM2', 'ACIN1', 'RNPS1', 'CLK1', 'CLK2', 'CLK3', 'CLK4']
if use_custom_list:
    genes_of_interest = custom_list
    print(f'\n -- NOTE -- Using custom list: {custom_list}')
else:
    genes_of_interest = KTC_GetGeneSet('m6a_erasers')

# =============================================================================
# Thresholds of significance and magnitude for noteworthy events
# =============================================================================
#Values below will be used to identify events of size and significance that we care to find and graph
thresh_pval       = 0.05 #Must be lower than
thresh_FDR        = 0.05 #Must be lower than (Significance metric used in rMATS)
thresh_PSI        = 0.2 #Must be more substantial than (value of delta Percent Spliced In)
thresh_l2FC       = 1.00 #Must be more substantial than
#Values below are used for details in figure
scale_factor      = 4 # Used to scale certain visuals of plots
dp_size           = 200 #Scales data points size
max_labels        = 20 # Set a limit on the number of events annotated with gene names. Prevents overcrowding.
unbiased          = False # If True, does not filter results based on genes of interest. Does not create a plot for these other genes but still prints gene names to the terminal for Enrichr etc.
only_plot_if_sign = False #Plots are only generated for each dataset if any significant events are found
plot_text         = True # Label data points with protein names
plot_legend       = True #Create legend for differential splicing plots (to identify types of events)
plot_mean_value   = False #Create a yellow vertical line at the mean of all values on the 1st axis
print_gene_names  = False #Print the names of events that clear the thresholds to the terminal
make_pdf          = True #Create a pdf that contains all plots
#Colors for events for genes_of_interest and genes not of interest
c_inte = '#4494c9' #blue
c_nint = '#dedede' #grey
#Colors for alternative splicing events
AS_colors   = {
	'SE'	: '#fc2c03', #Red
	'RI'	: '#b103fc', #Purple
	'MXE'   : '#fcba03', #Orange
	'A3SS'  : '#03fcfc', #Teal
	'A5SS'  : '#0380fc'  #Blue
		}

# =============================================================================
# Defining the structure of the PDF file
# =============================================================================
# Here, each key will be a page in a pdf with the values being a list of plots for that page (using the names for plots defined in of dict_df).
# A first page with info on launch parameters is automatically generated and the last two are populated dynamically
dict_pdf_layout = {
    # PRC2
    'Inhibitors of splicing and EZH2 and EZH2 KOs - Differential Expression' : ['PRC2_edgeR_E7107', 'PRC2_edgeR_Indisulam', 'PRC2_edgeR_Tazemetostat', 'PRC2_edgeR_KO1', 'PRC2_edgeR_KO2'],
    'Inhibitors of splicing and EZH2 and EZH2 KOs - Differential Splicing' : ['E7107_rMATS', 'E7070_rMATS', 'Tazemetostat_rMATS', 'KO1_rMATS', 'KO2_rMATS'],
    'Inhibitors of splicing and EZH2 and EZH2 KOs - Differential Proteomics' : ['E7107_v_DMSO_proteomics_perseus', 'E7070_v_DMSO_proteomics_perseus', 'Taz_v_DMSO_proteomics_perseus', 'KO1_v_DMSO_proteomics_perseus', 'KO2_v_DMSO_proteomics_perseus'],
    #Igor E7107 proteomics
    'DMSO vs 24h E7107 - Igor proteomics' : ['E7107_24_proteomics'],
    #High risk vs Low risk
    'High risk patients vs low risk patients - Differential Expression and Splicing' : ['risk_edgeR', 'risk_rMATS_kasper'],
    # Jonas T-ALL&STM 3seq, m6a, expression, splicing
    'T-ALL vs STM1 - Differential Expression and Splicing' : ['TallSTM_path_deseq', 'TallSTM_path_rMATS'],
    # T-ALL vs thymus
    'T-ALL vs thymus - Differential Expression and Splicing' : ['TALL_rMATS', 'TALL_deseq'],
    # Science Advances paper
    'Han, 2022, Science Advances - E7107, Differential Expression and Splicing' : ['E7107_TS2_24_splicing_rMATS', 'SciAdv_TS4_E7107_edgeR_15min', 'SciAdv_TS4_E7107_edgeR_1.5nm', 'SciAdv_TS4_E7107_edgeR_3.0nm'],
    'Han, 2022, Science Advances - shSF3B1, Differential Expression and Splicing' : ['SciAdv_TS5_shSF3B1_edgeR_1', 'SciAdv_TS5_shSF3B1_edgeR_1', 'SciAdv_TS3_shSF3B1_rMATS_1', 'SciAdv_TS3_shSF3B1_rMATS_2'],
    # NMD-related (from some Table 5 somewhere)
    'E7107 and NMDi-associated gene expression changes (CUTLL1, 24h)' : [],
    # Proteomics from Northwestern
    'Proteomics on E7107 treatment - Data from Northwestern' : []
    }

#%%This dictionary will contain pandas dataframes of all the Interesting Lists
#This cell takes a few minutes to run. If it has already been run and loaded into memory and no changes to the dataframe has been made - you could skip it.
dict_df = {
    #PRC2
    'PRC2_ATAC_E7070'                 : pd.read_csv(os.path.join(in_dir,   "contrast_ATAC_E7070_v_ctrl.tsv"), sep='\t'),
    'PRC2_ATAC_E7107'                 : pd.read_csv(os.path.join(in_dir,   "contrast_ATAC_E7107_v_ctrl.tsv"), sep='\t'),
    'PRC2_ATAC_Taz'                   : pd.read_csv(os.path.join(in_dir,   "contrast_ATAC_Taz_v_ctrl.tsv"), sep='\t'),
    'PRC2_ATAC_KO1'                   : pd.read_csv(os.path.join(in_dir,   "contrast_ATAC_KO1_v_ctrl.tsv"), sep='\t'),
    'PRC2_ATAC_KO2'                   : pd.read_csv(os.path.join(in_dir,   "contrast_ATAC_KO2_v_ctrl.tsv"), sep='\t'),
    #PRC2 rMATS
    'E7107_rMATS'                     : pd.read_excel(os.path.join(in_dir, 'PRC2_rMATS_results_PSI0.05_FDR0.1.xlsx'), sheet_name='E7107'),
    'E7070_rMATS'                     : pd.read_excel(os.path.join(in_dir, 'PRC2_rMATS_results_PSI0.05_FDR0.1.xlsx'), sheet_name='Indisulam'),
    'Tazemetostat_rMATS'              : pd.read_excel(os.path.join(in_dir, 'PRC2_rMATS_results_PSI0.05_FDR0.1.xlsx'), sheet_name='Tazemetostat'),
    'KO1_rMATS'                       : pd.read_excel(os.path.join(in_dir, 'PRC2_rMATS_results_PSI0.05_FDR0.1.xlsx'), sheet_name='KO1'),
    'KO2_rMATS'                       : pd.read_excel(os.path.join(in_dir, 'PRC2_rMATS_results_PSI0.05_FDR0.1.xlsx'), sheet_name='KO2'),
    #PRC2 edgeR
    'PRC2_edgeR_E7107'                : pd.read_csv(os.path.join(in_dir,   'edgeR_results_E7107.tsv'), sep='\t'),
    'PRC2_edgeR_Indisulam'            : pd.read_csv(os.path.join(in_dir,   'edgeR_results_Indisulam.tsv'), sep='\t'),
    'PRC2_edgeR_Tazemetostat'         : pd.read_csv(os.path.join(in_dir,   'edgeR_results_Tazemetostat.tsv'), sep='\t'),
    'PRC2_edgeR_KO1'                  : pd.read_csv(os.path.join(in_dir,   'edgeR_results_KO1.tsv'), sep='\t'),
    'PRC2_edgeR_KO2'                  : pd.read_csv(os.path.join(in_dir,   'edgeR_results_KO2.tsv'), sep='\t'),
    #PRC2 proteomics
    'E7070_v_DMSO_proteomics_perseus' : pd.read_csv(os.path.join(in_dir,   "E7070vsDMSO.txt"), sep='\t'),
    'E7107_v_DMSO_proteomics_perseus' : pd.read_csv(os.path.join(in_dir,   "E7107vsDMSO.txt"), sep='\t'),
    'Taz_v_DMSO_proteomics_perseus'   : pd.read_csv(os.path.join(in_dir,   "TazvsDMSO.txt"), sep='\t'),
    'KO1_v_DMSO_proteomics_perseus'   : pd.read_csv(os.path.join(in_dir,   "KO1vsDMSO.txt"), sep='\t'),
    'KO2_v_DMSO_proteomics_perseus'   : pd.read_csv(os.path.join(in_dir,   "KO2vsDMSO.txt"), sep='\t'),
    # Jonas T-ALL&STM 3seq, m6a, expression, splicing
    "TallSTM_path_rMATS"              : pd.read_excel(os.path.join(in_dir, "TALL&STM1.xlsx"), sheet_name='eclip_expression_splicing_data'),
    "TallSTM_path_deseq"              : pd.read_excel(os.path.join(in_dir, "TALL&STM1.xlsx"), sheet_name='m6a_with_expression_dataset'),
    #T-ALL vs. Thymus
    'TALL_rMATS'                      : pd.read_csv(os.path.join(in_dir,   "thymus_v_TALL_rMATS_compiled.tsv"), sep='\t'),
    'TALL_deseq'                      : pd.read_excel(os.path.join(in_dir, "TALL1. Expression DE-SEQ T_All vs Thymus_BE-March, 2023.xlsx"), sheet_name='Blad1'),
    #Igor proteomics on 24h incubation with E7107
    "E7107_24_proteomics"             : pd.read_csv(os.path.join(in_dir,   "DMSOvs24hE7107.csv")),
    # High Risk versus Low Risk
    'risk_edgeR'                      : pd.read_excel(os.path.join(in_dir, "HRvsLR1. Expression Low-Risk_VS_High-Risk.htseq.edgeR.xlsx"), sheet_name='Low-Risk_VS_High-Risk.htseq.edg'),
    'risk_rMATS_kasper'               : pd.read_csv(os.path.join(in_dir,   "rmats_combined_analysis.tsv"), sep='\t'),
    #Han et al. transcription changes are dose-dependent on inhibition by E7107 
    "E7107_TS2_24_splicing_rMATS"     : pd.read_excel(os.path.join(in_dir, "E7107-induced splicng changes sciadv.abj8357_table_s2.xlsx"), sheet_name="24h FDR<0.05 PSI>0.1", skiprows=1),
    "SciAdv_TS4_E7107_edgeR_15min"    : pd.read_excel(os.path.join(in_dir, "SciAdv_TS4_E7107_DoseDependent_edgeR.xlsx"), sheet_name='DMSO_vs_E7107_15min.htseq.edgeR'), #Table S4. E7107-associated gene expression changes (CUTLL1, 15min)
    "SciAdv_TS4_E7107_edgeR_1.5nm"    : pd.read_excel(os.path.join(in_dir, "SciAdv_TS4_E7107_DoseDependent_edgeR.xlsx"), sheet_name='DMSO_vs_E7107_1.5nm.htseq.edgeR'), #Table S4. E7107-associated splicing events changes in CUTLL1 cells (1.5nm)
    "SciAdv_TS4_E7107_edgeR_3.0nm"    : pd.read_excel(os.path.join(in_dir, "SciAdv_TS4_E7107_DoseDependent_edgeR.xlsx"), sheet_name='DMSO_vs_E7107_3nm.htseq.edgeR'), #Table S4. E7107-associated gene expression changes in CUTLL1 cells (3nm)
    #Han et al. Silencing SF3B1 leads to inhibition of DDR (DNA damage response)
    #"SciAdv_TS5_E7107_edgeR"	   : pd.read_excel(SciAdv_TS5_shSF3B1_edgeR, sheet_name='DMSO_vs_3nM_E7107.htseq.edgeR'), #Table S5. E7107 vs vehicle gene expression changes in CUTLL1 cells. Appears to be identical to "SciAdv_TS4_E7107_edgeR_3.0nm"
    "SciAdv_TS5_shSF3B1_edgeR_1"      : pd.read_excel(os.path.join(in_dir, "SciAdv_TS5_shSF3B1_edgeR.xlsx"), sheet_name='shCtrl_vs_shSF3B1.1.htseq.edgeR'), #Table S5. shSF3B1.1-associated gene expression changes in CUTLL1 cells
    "SciAdv_TS5_shSF3B1_edgeR_2"      : pd.read_excel(os.path.join(in_dir, "SciAdv_TS5_shSF3B1_edgeR.xlsx"), sheet_name='shCtrl_vs_shSF3B1.2.htseq.edgeR'), #Table S5. shSF3B1.2-associated gene expression changes in CUTLL1 cells
    #Han et al. Splicing alterations caused by SF3B1 silencing is similar to E7107 inhibition
    "SciAdv_TS3_shSF3B1_rMATS_1"      : pd.read_excel(os.path.join(in_dir, "SciAdv_TS3_shSF3B1_rMATS.xlsx"), sheet_name='shSF3B1.1 VS control'), # Table S3. shSF3B1.1-associated splicing events changes in CUTLL1 cells
    "SciAdv_TS3_shSF3B1_rMATS_2"      : pd.read_excel(os.path.join(in_dir, "SciAdv_TS3_shSF3B1_rMATS.xlsx"), sheet_name='shSF3B1.2 VS control') #Table S3. shSF3B1.2-associated splicing events changes in CUTLL1 cells
    }
#%% ANALYSIS - Run this cell to execute script
plot_path_list = [] # Will contain paths to all figures generated for pdf generation. Populated automatically.

# =============================================================================
# Volcano Plot function
# =============================================================================
x_window = 1 # Clamps the x-axis of differential splicing (all values are between -1 and 1)
min_pval = 0.00000000000000000001 # Used as a ceiling to limit the scale of the 2nd axis with miniscule p-values

def pval_Clamper(_float):
	if _float < min_pval:
		return min_pval
	else:
		return _float

#This is the main function for generating volcano plots. It takes data and a type of plot (splicing, DGE, proteomics).
def Volcano(dict_volcano, name, analType):
    print("Making figure for: %s" %(name), analType)
    plt.figure(figsize=(10,10))

    i_Xs = dict_volcano['i_X']
    i_Ys = dict_volcano['i_Y']
    ni_Xs = dict_volcano['ni_X']
    ni_Ys = dict_volcano['ni_Y']

    plt.scatter(ni_Xs, ni_Ys, color=c_nint, s=200)

    max_value = max(max(i_Ys), max(ni_Ys)) if i_Ys else max(ni_Ys)
    plt.ylim(0, max_value * 1.05)

    # Generate a vertical line for the mean of X-values (considering only statistically significant data)
    if plot_mean_value:
        filtered_iXs = [i_Xs[i] for i in range(len(i_Xs)) if i_Xs[i] > thresh_FDR]
        filtered_niXs = [ni_Xs[i] for i in range(len(ni_Xs)) if ni_Xs[i] > thresh_FDR]
        mean = sum(filtered_iXs + filtered_niXs) / len(filtered_iXs + filtered_niXs)
        plt.axvline(mean, color='yellow')

    texts = []
    if i_Xs and i_Ys:  # Only annotate if there are significant genes
        # Pair the data points with their labels
        labeled_points = [(abs(i_Xs[i]), i_Xs[i], i_Ys[i], dict_volcano['geneSymbols'][i]) for i in range(len(i_Xs))]
        # Sort points by absolute x-value in descending order and take the top max_labels
        labeled_points = sorted(labeled_points, reverse=True)[:max_labels]
    
        for _, x, y, label in labeled_points:
            if plot_text:
                texts.append(plt.text(x, y, label, fontsize=6 * scale_factor))
        # Adjust text positions to avoid overlap (optional if adjust_text is used)
        adjust_text(texts)

    #If this is differential expression
    if analType == "DE_expression":
        if i_Xs and i_Ys:  # Only scatter significant points
            plt.scatter(i_Xs, i_Ys, color=c_inte, s=dp_size)
        plt.axhline(-math.log10(thresh_pval), color='black', alpha=0.5)
        plt.axvline(thresh_l2FC, color='black', alpha=0.5)
        plt.axvline(-thresh_l2FC, color='black', alpha=0.5)
        plt.xlabel('log2(Fold Change)', fontsize=10*scale_factor)
        plt.ylabel('-log10(adj. p-value)', fontsize=10*scale_factor)

    # If this is differential splicing
    elif analType == "DE_splicing":
        if i_Xs and i_Ys:  # Only scatter significant points
            plt.scatter(i_Xs, i_Ys, c=[AS_colors[type_] for type_ in AS_list], s=dp_size)
        plt.axhline(-math.log10(thresh_pval), color='black', alpha=0.5)
        plt.axvline(thresh_PSI, color='black', alpha=0.5)
        plt.axvline(-thresh_PSI, color='black', alpha=0.5)
        plt.xlabel('ΔPSI', fontsize=10*scale_factor)
        plt.ylabel('-log10(p-value)', fontsize=10*scale_factor)
        plt.xlim(-x_window, x_window)
        plt.xticks([-1, -0.5, 0, 0.5, 1])
        plt.grid(alpha=0.2)
        if plot_legend:
            legend_entries = [(type_, plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=AS_colors[type_], markersize=8)) for type_ in set(AS_list)]
            plt.legend([entry[1] for entry in legend_entries], [entry[0] for entry in legend_entries], fontsize=6*scale_factor, markerscale=2, loc='upper left')

    # If this is proteomics
    elif analType == "DE_proteomics":
        if i_Xs and i_Ys:  # Only scatter significant points
            plt.scatter(i_Xs, i_Ys, color=c_inte, s=dp_size)
        plt.axhline(-math.log10(thresh_pval), color='black', alpha=0.5)
        plt.axvline(thresh_l2FC, color='black', alpha=0.5)
        plt.axvline(-thresh_l2FC, color='black', alpha=0.5)
        # plt.xlim(-x_window, x_window)
        plt.xlabel('log2(Fold Change)', fontsize=8*scale_factor)
        # plt.ylabel('-log10(p-value)', fontsize=15*scale_factor)
        # plt.title("Protein changes upon E7107 treatment", fontsize=8*scale_factor)
        # plt.xticks([-1, -0.5, 0, 0.5, 1])

    if not i_Xs or not i_Ys:  # If no significant data, display a message
        plt.gcf().text(0.5, 0.5, 'No significant events found', fontsize=12 * scale_factor, ha='center', va='center', color='red')

    plt.title(name, fontsize=8*scale_factor)
    plt.xticks(fontsize=8*scale_factor)
    plt.yticks(fontsize=8*scale_factor)
    ax = plt.gca()
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    path_file_out = out_dir + name + '.png'
    plot_path_list.append(path_file_out)
    plt.savefig(path_file_out)
    plt.show()
    plt.close()


# ===========================================================================
# Analysis and visualization
# =============================================================================
#This dictionary contains genenames as keys with a numbers as values for how many times it has appeared across different dataframes (max once per dataframe)
#Thus if a gene clears the thresholds in seven dataframes it will have a value of seven (useful for ranking genes that seem relevant across different experiments)
#This is only to try and find genes that appear frequently across many dataframes with significant events. It is not vital to produce graphs for individual genes.
appearances = {}
def add_appearance(geneName, alreadyAdded):
	if geneName not in alreadyAdded:
		if geneName in appearances:
			alreadyAdded.append(geneName)
			appearances[geneName] += 1
		else:
			appearances[geneName] = 1

# Iterating through the dataframes and generating graphs
print('--- Settings ---')
print('pVal <%.2f' %thresh_pval)
print('PSI  >%.2f' %thresh_PSI)
print('FDR  <%.2f' %thresh_FDR)
print('l2FC >%.2f' %thresh_l2FC)
print()
print('Genes searched:')
print(' '.join(sorted(genes_of_interest)))

#Here we loop through each dataframe and feed the necessary data to the Volcano function
for df_key in dict_df:
    print()
    df = dict_df[df_key]
    unbiased_geneSymbols = []

    # If we are dealing with differential splicing
    if 'rMATS' in df_key:
        alreadyAdded = []
        print(df_key)
        if print_gene_names:
            print('Gene,Event,pVal,FDR,PSIdiff')
        dict_volcano = {'ni_X' : [], 'ni_Y' : [], 'i_X' : [], 'i_Y' : [], 'geneSymbols': []}
        AS_list	     = []
        for index, row in df.iterrows():
            gene = row['geneSymbol']
            pval = row['PValue']
            FDR  = row['FDR']
            PSI  = row['IncLevelDifference']
            SplE = row['Splicing Event']
            PSI = PSI * -1
            if SplE == 'SE': # There is discussion whether skipped exon events need to be flipped
                PSI = PSI * -1
            line = '%s,%s,%.3f,%.3f,%.3f' %(gene, SplE, pval, FDR, PSI)
            if 'nan' in line:
                continue
            if gene in genes_of_interest and pval < thresh_pval and FDR < thresh_FDR and abs(PSI) >= thresh_PSI:
                if print_gene_names:
                    print(line)
                dict_volcano['i_X'].append(PSI)
                dict_volcano['i_Y'].append(-math.log10(pval_Clamper(pval)))
                dict_volcano['geneSymbols'].append(gene)
                AS_list.append(SplE)
            else:
                dict_volcano['ni_X'].append(-PSI)
                dict_volcano['ni_Y'].append(-math.log10(pval_Clamper(pval)))
            if unbiased:
                if pval < thresh_pval and FDR < thresh_FDR and abs(PSI) >= thresh_PSI:
                    if type(gene) == type(''):
                        unbiased_geneSymbols.append(str(gene))
            if pval < thresh_pval and FDR < thresh_FDR and abs(PSI) >= thresh_PSI:
                add_appearance(gene, alreadyAdded)
        if only_plot_if_sign == False:
            Volcano(dict_volcano, df_key, "DE_splicing")
        elif only_plot_if_sign and len(dict_volcano['i_Y']) > 0:
            Volcano(dict_volcano, df_key, "DE_splicing")
        else:
            print(f'skipping {df_key}: no significant events found')

    # If we are looking at differential expression
    elif 'edgeR' in df_key or 'deseq' in df_key or 'ATAC' in df_key:
        alreadyAdded = []
        print(df_key)
        if print_gene_names:
            print('Gene,pVal,log2FC')
        dict_volcano = {'ni_X' : [], 'ni_Y' : [], 'i_X' : [], 'i_Y' : [], 'geneSymbols': []}
        for index, row in df.iterrows():
            if 'edgeR' in df_key:
                gene = row['geneSymbol']
                l2FC = row['log2FC']
            else:
                gene = row['gene_symbol']
                l2FC = row['log2FoldChange']
            pval = row['padj']
            line = '%s,%.3f,%.3f' %(gene, pval, l2FC)
            if gene in genes_of_interest and pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                if print_gene_names:
                    print(line)
                dict_volcano['i_X'].append(l2FC)
                dict_volcano['i_Y'].append(-math.log10(pval_Clamper(pval)))
                dict_volcano['geneSymbols'].append(gene)
            else:
                dict_volcano['ni_X'].append(l2FC)
                dict_volcano['ni_Y'].append(-math.log10(pval_Clamper(pval)))
            if unbiased:
                if pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                    if type(gene) == type(''):
                        unbiased_geneSymbols.append(str(gene))
            if pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                add_appearance(gene, alreadyAdded)
        if only_plot_if_sign == False:
            Volcano(dict_volcano, df_key, "DE_expression")
        elif only_plot_if_sign and len(dict_volcano['i_Y']) > 0:
            Volcano(dict_volcano, df_key, "DE_expression")
        else:
            print(f'skipping {df_key}: no significant events found')

    # If we are looking at proteomics data
    elif 'proteomics' in df_key:
        alreadyAdded = []
        print(df_key)
        if print_gene_names:
            print('Gene,pVal,log2FC')
        dict_volcano = {'ni_X' : [], 'ni_Y' : [], 'i_X' : [], 'i_Y' : [], 'geneSymbols': []}
        for index, row in df.iterrows():
            if 'perseus' in df_key:
                gene = row['Genes']
                l2FC = row['Difference']
                neglogpval = row['-Log(P-value)']
                pval = 10**(-1*neglogpval)
            else:
                gene = row['GeneSymbol']
                l2FC = row['log2FC']
                neglogpval = row['neglogPVal']
                pval = 10**(-1*neglogpval)
            line = '%s,%.3f,%.3f' %(gene, pval, l2FC)
            if gene in genes_of_interest and pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                if print_gene_names:
                    print(line)
                dict_volcano['i_X'].append(l2FC)
                dict_volcano['i_Y'].append(-math.log10(pval_Clamper(pval)))
                dict_volcano['geneSymbols'].append(gene)
            else:
                dict_volcano['ni_X'].append(l2FC)
                dict_volcano['ni_Y'].append(-math.log10(pval_Clamper(pval)))
            if unbiased:
                if pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                    if type(gene) == type(''):
                        unbiased_geneSymbols.append(str(gene))
            if pval < thresh_pval and abs(l2FC) >= thresh_l2FC:
                if type(gene) == type(''):
                    add_appearance(gene, alreadyAdded)
        if only_plot_if_sign == False:
            Volcano(dict_volcano, df_key, "DE_proteomics")
        elif only_plot_if_sign and len(dict_volcano['i_Y']) > 0:
            Volcano(dict_volcano, df_key, "DE_proteomics")
        else:
            print(f'skipping {df_key}: no significant events found')

    else:
        print('\n!!data type not found for %s!!' %(df_key))

    line = ''

    if unbiased:
        print()
        print("Hits with no prefiltering based on genenames:")
        print('\n'.join(unbiased_geneSymbols))


# =============================================================================
# NMDi rescue
# =============================================================================
# Loading in the data on NMDi rescue
df_E7107_rescue = pd.read_excel(os.path.join(in_dir, "NMD-related-Table 5. E7107 and NMDi-associated gene exprression changes (CUTLL1, 24h).xlsx"), sheet_name="E7107_vs_E7107-NMDi.htseq.edgeR", skiprows=1)

# Creating graphs for NMDi rescue
import seaborn as sns
import numpy as np

samples = ["CUTLL1.3nM.E7107.Rep1", "CUTLL1.3nM.E7107.Rep2", "CUTLL1.3nM.E7107.Rep3", "CUTLL1.3nM.E7107.5uM.NMDi.Rep1", "CUTLL1.3nM.E7107.5uM.NMDi.Rep2", "CUTLL1.3nM.E7107.5uM.NMDi.Rep3"]


for protein in sorted(genes_of_interest):
    ctrl_values = []
    nmdi_values = []

    for index, row in df_E7107_rescue.iterrows():
        gene = row["gene"]
        pval = row["adj.p"]
        l2FC = row["logFC"]
        
        if gene == protein:
            for sample in samples:
                if "NMDi" in sample:
                    nmdi_values.append(row[sample])
                else:
                    ctrl_values.append(row[sample])

    plt.figure(figsize=(10,10))
    sns.set(style="whitegrid", rc={"axes.grid": True, "grid.linestyle": "-"})

    _data = {
            "Ys" : np.concatenate([ctrl_values, nmdi_values]), 
            "Condition" : np.repeat(["E7107", "E7107+NMDi"], [3, 3])
            }


    if ctrl_values and nmdi_values:
        _mean_control   = np.mean(ctrl_values)
        _mean_treatment = np.mean(nmdi_values)

        df_data = pd.DataFrame(_data)
        max_value = df_data["Ys"].max()
        p = sns.stripplot(x="Condition", y="Ys", data=_data, jitter=0.3, size=40, edgecolor="white", linewidth=4)

        sns.boxplot(showmeans=True,
                    meanline=True,
                    meanprops={'color': 'k', 'ls': '-', 'lw': 2},
                    medianprops={'visible': False},
                    whiskerprops={'visible': False},
                    zorder=10,
                    x="Condition",
                    y="Ys",
                    data=_data,
                    showfliers=False,
                    showbox=False,
                    showcaps=False,
                    ax=p
                    )
        plt.ylim(0, max_value*1.2)

    else:
        plt.gcf().text(0.5, 0.5, '%s\nnot found in data' %(protein), fontsize=12 * scale_factor, ha='center', va='center', color='red')
        print('NMDi plot failed for: %s' %(protein))

    path_file_out = out_dir + '%s_E7107_NMDi_rescue.png' %(protein)
    plot_path_list.append(path_file_out)
    dict_pdf_layout['E7107 and NMDi-associated gene expression changes (CUTLL1, 24h)'].append(os.path.basename(path_file_out).split('.png')[0])
    plt.xlabel("", fontsize=30)
    plt.ylabel('counts', fontsize=50)
    plt.title("%s" %(protein), fontsize=60)
    plt.xticks(fontsize=50)
    plt.yticks(fontsize=50)
    plt.savefig(path_file_out)
    plt.show()
    plt.close()


# =============================================================================
# Mass spectrometry on E7107 treatment
# =============================================================================
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

df = pd.read_excel(os.path.join(in_dir, "PN 031821_tc-786_Marinaccio_C_humanTMT16_Northwestern.xlsx"), sheet_name="tc-786_proteinquant", skiprows=4, header=1)

samples = {
    "DMSO"     : ["129C", "130N", "130C"],
    "E7107" : [ "131N", "131C", "132N", "132C"]
    }

for p in sorted(genes_of_interest):
    protein = p
    values = {
        "DMSO"     : [],
        "E7107" : []
        }
    for index, row in df.iterrows():
        try:
            protein_desc = row["Protein Description"]
            geneSymbol   = protein_desc.split("GN=")[1].split()[0]
        except:
            continue
        if geneSymbol == protein:
            for condition in samples:
                for sample in samples[condition]:
                    sample_ID = sample + ".1"
                    value = row[sample_ID]
                    values[condition].append(value)
    _data = {
            "Ys" : np.concatenate([values["DMSO"], values["E7107"]]), 
            "Condition" : np.repeat(["DMSO", "E7107"], [len(values["DMSO"]), len(values["E7107"])])
            }
    plt.figure(figsize=(10,10))
    plt.xlabel('', fontsize=60)
    plt.ylabel('Normalized relative\nabundance', fontsize=60)
    plt.title("%s levels on inhibition of splicing" %(protein), fontsize=40)
    sns.set(style="whitegrid", rc={"axes.grid": True, "grid.linestyle": "-"})

    _mean_control   = np.mean(values["DMSO"])
    _mean_treatment = np.mean(values["E7107"])

    df_data = pd.DataFrame(_data)
    max_value = df_data["Ys"].max()
    if len(_data["Ys"]) > 0:
        p = sns.stripplot(x="Condition", y="Ys", data=_data, jitter=0.3, size=40, edgecolor="white", linewidth=4)
        sns.boxplot(showmeans=True,
                    meanline=True,
                    meanprops={'color': 'k', 'ls': '-', 'lw': 2},
                    medianprops={'visible': False},
                    whiskerprops={'visible': False},
                    zorder=10,
                    x="Condition",
                    y="Ys",
                    data=_data,
                    showfliers=False,
                    showbox=False,
                    showcaps=False,
                    ax=p
                )
        plt.ylim(0, max_value*1.2)
        plt.xticks(fontsize=50)
        plt.yticks(fontsize=50)
    else:
        plt.gcf().text(0.5, 0.5, '%s\nnot found in data' %(protein), fontsize=12 * scale_factor, ha='center', va='center', color='red')

    path_file_out = out_dir + 'E7107_MS_%s.png' %(protein)
    plot_path_list.append(path_file_out)
    # print(os.path.basename(path_file_out).split('.png')[0])
    dict_pdf_layout['Proteomics on E7107 treatment - Data from Northwestern'].append(os.path.basename(path_file_out).split('.png')[0])
    plt.savefig(path_file_out)
    plt.show()
    plt.close()

# =============================================================================
# Generating a pdf
# =============================================================================

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import image as mpimg
from collections import defaultdict
import textwrap

genes_sorted = '  '.join(sorted(genes_of_interest))
first_page_lines = [

    'Only events that clear thresholds of significance are highlighted:',
    f'FDR threshold (rMATS): <{thresh_FDR}',
    f'pval threshold (others): <{thresh_pval}',
    f'dPSI threshold (rMATS): >= abs({thresh_PSI})',
    f'l2FC threshold (others): >= abs({thresh_l2FC})',
    f'maximum text annotations per plot:  {max_labels}',
    'Genes searched:',
    f'{genes_sorted}'
    ]

def organize_plots_into_pages(plot_path_list, dict_pdf_layout):
    # Reverse the layout to map plot names to page keys
    name_to_page = {}
    for page, plot_names in dict_pdf_layout.items():
        for name in plot_names:
            name_to_page[name] = page

    # Group paths by page
    pages = defaultdict(list)
    for path in plot_path_list:
        # Extract plot name from the file path
        plot_name = os.path.basename(path).replace(".png", "")  # Assumes .png extension
        if plot_name in name_to_page:
            page_key = name_to_page[plot_name]
            pages[page_key].append(path)
    return pages


if make_pdf:
    # Organize plots into pages
    pages = organize_plots_into_pages(plot_path_list, dict_pdf_layout)
    
    import math
    
    def calculate_grid_dimensions(n_items):
        """
        Calculate the number of rows and columns for a grid layout
        based on the total number of items.
        """
        if n_items == 1:
            return 1, 1  # Special case for a single plot
        cols = math.ceil(math.sqrt(n_items))  # Start with a square grid
        rows = math.ceil(n_items / cols)  # Adjust rows to fit all items
        return rows, cols

    # Create the PDF
    with PdfPages(path_pdf) as pdf:
        # Create the first page with parameters
        fig, ax = plt.subplots(figsize=(8.3, 11.7))  # A4 dimensions in inches
        ax.axis('off')  # No axes needed for the text page
        # Title
        plt.text(0.5, 0.95, "Launch Parameters:", fontsize=20, ha='center', va='top', transform=ax.transAxes)
        # Parameters list
        y_start = 0.85
        line_spacing = 0.035
        wrap_width=70

        for idx, string in enumerate(first_page_lines):
            # Wrap the string
            wrapped_lines = textwrap.wrap(string, width=wrap_width)
            # Plot each line separately
            for line_idx, line in enumerate(wrapped_lines):
                plt.text( 0.1, y_start - (idx + line_idx * 0.5) * line_spacing, line, fontsize=10, ha='left', va='top', transform=ax.transAxes)
        # Save the first page
        pdf.savefig(fig)
        plt.close(fig)

        for page_title, paths in pages.items():
            print(page_title)
            n_plots = len(paths)
            rows, cols = calculate_grid_dimensions(n_plots)  # Dynamically determine grid size
            # Get dynamic figure size based on the number of plots
            fig_width, fig_height = (cols*3, rows*3)
            
            fig, axes = plt.subplots(
                nrows=rows, ncols=cols, figsize=(fig_width, fig_height)
            )  # Dynamic size
            axes = np.array(axes).reshape(-1)  # Flatten axes for easy iteration
    
            # Handle fewer plots than grid cells
            for ax, path in zip(axes[:n_plots], paths):
                img = mpimg.imread(path)
                ax.imshow(img, aspect='auto')
                ax.axis("off")
    
            # Turn off unused axes
            for ax in axes[n_plots:]:
                ax.axis("off")
    
            plt.suptitle(page_title, wrap=True)  # Title for the page
            plt.subplots_adjust(top=0.85)  # Adjust top to make room for the title
            # plt.tight_layout()
            pdf.savefig(fig, dpi=300)
            plt.close(fig)
    
    print(f"PDF saved as {path_pdf}")
else:
    print('PDF not requested')


#%% To satisfy the curious, this section prints out the genes that appear the most across all scanned dataframes
thresh_appearance_fraction = 3 # A gene must appear in at least 1 in every n dataframes to be considered a frequent hit
thresh_appearances = math.ceil(len(dict_df)/thresh_appearance_fraction) #How many dataframes must a gene have been seen in before it is interesting?
frequent_genes = [key for key, value in appearances.items() if value >= thresh_appearances]
frequent_genes_sorted = sorted(frequent_genes, key=lambda k: appearances[k], reverse=True)
print()
print("Genes found %i or more times in the %i dataframes:" %(thresh_appearances, len(dict_df)))
for gene in frequent_genes_sorted:
    print(gene, appearances[gene])
