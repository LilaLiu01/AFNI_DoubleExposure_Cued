#! /bin/sh

# Getting data from dicombliss
ssh dicombliss
cp -r /opt/dicom_storage/20240313-ST001-5063-tia-sub1/ /pkg/classes/psych5063/Spring2024/data/.
cp -r /opt/dicom_storage/20240319* /pkg/Spring2023/data/.
chmod g-w -R /pkg/Spring2023/data/2023*

cd /pkg/Spring2023/playground
mkdir liu02542
ln -s /pkg/Spring2023/data/double_expo houseface
	… except use the full path to your group’s data, and whatever you want to name your link …

# Set up Freesurfer
qsub -IX
tcsh
cd /pkg/Spring2023/playground/liu02542
module load freesurfer
setenv SUBJECTS_DIR /pkg/Spring2023/freesurfer_outputs

recon-all -all -gcut -s houseface -i /PATH/TO/FIRST/DICOM/OF/SECOND/T1/SCAN
module load afni

# Organize data
mv houseface dicom
mkdir func
mkdir func/orig

# Convert each scan with systematic name
module load mricrogl
dcm2niix -o func/orig -f run00_ABCD dicom/MR-SE0YY-WXYZ

# Motion compensation
module load afni
3dvolreg -overwrite -zpad 4 -1Dfile run0X_param.1D -1Dmatrix_save
run0X_within.aff12.1D -prefix run0X_ABCD_moco.nii run0X_ABCD.nii

# Single-volume averages of each motion-corrected scan
3dTstat -prefix run0X_mean.nii run0X_ABCD_moco.nii
cp run00_mean.nii moco_base.nii

# Recursively make transformation matrix that aligns each scan to the base reference
3dAllineate -overwrite -1Dmatrix_save run0X_between.aff12.1D -base moco_base.nii
-input run0X_mean.nii -cost lpa -prefix run0X_between.nii -source_automask+2
-warp shift_rotate -verb -final wsinc5

# Create a motion-compensated copy of the data
cd ..
mkdir moco
cp orig/run00_within.aff12.1D moco/run00_xform.1D
cat_matvec orig/run0X_between.aff12.1D orig/run0X_within.aff12.1D >
moco/run0X_xform.1D

3dAllineate -overwrite -input orig/run0X_ABCD.nii -1Dmatrix_apply
moco/run0X_xform.1D -prefix moco/run0X_ABCD.nii -final wsinc5

cd moco
afni

# Distortion compensation
qsub -IX
tcsh
module load afni
module load mricrogl

cd /pkg/classes/psych5063/Spring2024/playground/liu02542
mkdir func/unwarp
dcm2niix -o func/unwarp -f PErev dicom/PE_REV_DIRECTORY
3dTstat -overwrite -prefix func/unwarp/PErev.nii func/unwarp/PErev.nii

3dTstat -overwrite -prefix func/unwarp/PEreg.nii func/moco/run00_ABCD.nii

# Run 3dQwarp to discover the unwarp fields
cd func/unwarp
3dQwarp -source PEreg.nii -base PErev.nii -pblur -noZdis -noXdis -prefix QWARP
-plusminus -superhard -minpatch 9 -Qfinal

# Apply the correct WARP field to all data
cd ..
# for each of scans
3dNwarpApply -overwrite -source moco/run0X_ABCD.nii -nwarp
'unwarp/QWARP_PLUS_WARP+orig' -prefix unwarp/run0X_ABCD.nii

# Run GLM
# Create stimulus timing files
mkdir experiment # save all those .txt files in the experiment folder

# Create a “% signal change” version of the preprocessed data
cd unwarp
mkdir scaled
# Recursively
3dTstat -overwrite -prefix runXX_XXXX_mean.nii runXX_XXXX.nii
3dcalc -overwrite -prefix scaled/runXX_XXXX.nii -a runXX_XXXX.nii -b runXX_XXXX_mean.nii -expr ‘a/b’
3dcalc -overwrite -prefix scaled/runXX_XXXX.nii -a scaled/runXX_XXXX.nii -expr ‘100*a’

# Real GLM
mkdir glm
tcsh combine_regressors.sh
3dDeconvolve -overwrite -jobs 8 -polort 2 -float -fout -tout        \
  -bucket stats_only_house.nii                                      \
  -input func/unwarp/scaled/run02_house_only.nii                    \
         func/unwarp/scaled/run06_house_only.nii                    \
  -num_stimts 4 -local_times                                        \
  -stim_times 1 experiment/only_house_stim.txt 'GAM' -stim_label 1 stim     \
  -stim_times 2 experiment/only_house_ramp.txt 'GAM' -stim_label 2 ramp     \
  -stim_times 3 experiment/only_house_noise.txt 'GAM' -stim_label 3 noise   \
  -stim_times 4 experiment/only_house_button.txt 'GAM' -stim_label 4 button \
  -gltsym 'SYM: .33*stim +.33*ramp +.33*noise' -glt_label 1 'all_stim'

# Look at data
3dTstat -prefix glm/epi.nii func/unwarp/run00_ABCD.nii
cd glm
module load afni

# Add a contrast between conditions
3dDeconvolve -overwrite -jobs 8 -polort 5 -float -fout -tout \
  -bucket glm/stats_task_unwarp.nii 					 \
  -x1D glm/X.xmat_task_unwarp.1D                             \
  -input func/unwarp/scaled/run00_task.nii                   \
  -num_stimts 3 -local_times                                 \
  -stim_times 1 experiment/describe.txt 'BLOCK(20,1)' -stim_label 1 describe \
  -stim_times 2 experiment/imagine.txt 'BLOCK(20,1)' -stim_label 2 imagine   \
  -stim_times 3 experiment/rating.txt 'BLOCK(25,1)' -stim_label 3 rating     \
  -gltsym 'SYM: imagine -describe' -glt_label 1 'my_contrast'

# Register functional and anatomical data
mkdir vol
cp func/unwarp/run00_XXXX.nii vol/epi.nii

3dAFNItoNIFTI -prefix vol/anat_SurfVol.nii
/pkg/Spring2023/freesurfer_outputs/houseface/SUMA/anat_SurfVol+orig
align_epi_anat.py -epi epi.nii -epi_base mean -anat anat_SurfVol.nii -giant_move
3dAFNItoNIFTI -prefix anat_to_func.nii anat_SurfVol_al+orig

cd ../glm
ln -s ../vol/anat_to_func.nii

# Create own space for AFNI and SUMA to communicate
setenv AFNI_PORT_OFFSET 0128
echo $AFNI_PORT_OFFSET

afni -niml & suma -spec
/pkg/classes/psych5063/Spring2024/freesurfer_outputs/team_XXXX/SUMA/anat_both.spec -sv anat_to_func.nii

# Standardizing the anatomy
@auto_tlrc -base TT_N27+tlrc -input anat_SurfVol.nii
align_epi_anat.py -epi epi.nii -epi_base mean -anat anat_SurfVol.nii -giant_move -epi2anat -tlrc_apar anat_SurfVol_at.nii











