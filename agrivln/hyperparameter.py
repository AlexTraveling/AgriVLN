# AgriVLN - The Hyperparameters Database

def get_hyperparameter(name):

   hyperparameter_dic = {
      "interval": 0.2,
      "threshold": 4.0,
      "speed": 1.3,
      "SR_threshold": 2.0,
      "accuracy_threshold": 0.5
   }

   return hyperparameter_dic[name]
