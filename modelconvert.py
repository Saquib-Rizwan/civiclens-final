from tensorflow import keras

# Load and resave the model with correct serialization format
model = keras.models.load_model("ai_model/model.h5")
model.save("ai_model/model.h5", save_format="h5")
