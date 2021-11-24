"""
From now on, any newly crawled dataset will have their DATS.json file
going through all validator checks. We will contact the owners of the
datasets previously uploaded later on to ask them to update their DATS
file but in the meantime, the list below will skip the non_schema_required
checks for the data already existing in the portal.
That list will be updated as the owners of the datasets update their DATS
files once we contact them.

TODO: when there is no more dataset in this list, remove the if statement
TODO: from template.py that checks if the dataset is part of the list
"""
RETROSPECTIVE_CRAWLED_DATASET_LIST = [
    "projects/CFMM_7T__MP2RAGE_T1_mapping",
    "projects/Calgary_Preschool_MRI_Dataset",
    "projects/Comparing_Perturbation_Modes_for_Evaluating_Instabilities_in_Neuroimaging__Processed_NKI_RS_Subset__08_2019_",  # noqa: E501
    "projects/Intracellular_Recordings_of_Murine_Neocortical_Neurons",
    "projects/Learning_Naturalistic_Structure__Processed_fMRI_dataset",
    "projects/MRI_and_unbiased_averages_of_wild_muskrats__Ondatra_zibethicus__and_red_squirrels__Tamiasciurus_hudsonicus_",  # noqa: E501
    "projects/Multimodal_data_with_wide_field_GCaMP_imaging",
    "projects/Numerically_Perturbed_Structural_Connectomes_from_100_individuals_in_the_NKI_Rockland_Dataset",
    "projects/Quantifying_Neural_Cognitive_Relationships_Across_the_Brain",
    "projects/Synthetic_Animated_Mouse__SAM___University_of_British_Columbia__Datasets_and_3D_models",
    "projects/VFA_T1_mapping___RTHawk__open__vs_Siemens__commercial_",
]
