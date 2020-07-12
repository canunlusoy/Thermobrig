from ThermalProperties.ThprOps import fullyDefine_StatePure
import Utilities.FileOps
from ThermalProperties.States import StatePure

dataFile_path = r'D:\Belgeler\İşler\Thermobrig\Thermodynamic Property Data\Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = Utilities.FileOps.read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
MaterialPropertyDF = Utilities.FileOps.process_MaterialPropertyDF(dataFile)

statePropt = {'T':500, 'P':500}
testState = StatePure(**{'T':500, 'x':0.5})
state = fullyDefine_StatePure(testState, MaterialPropertyDF)
pass

