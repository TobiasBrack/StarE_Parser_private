clc
close all
clearvars

%% 
filedir = "CR4532Adjustment/matlab/UC35/2DSG_Bismuth (271.44°C, 52.16 J_g)_@2,5,10K_2.7958mg_S3_parsed/2DSG_Bismuth (271.44°C, 52.16 J_g)_@2,5,10K_2.7958mg_S3.json";

data = jsondecode(fileread(filedir))