import os
import base64
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image
import tensorflow as tf
from langchain_core.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

# Ensure uploads directory exists
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# Model paths
MODELS_DIR = Path("models")
MODEL_PATHS = {
    "apple": MODELS_DIR / "Apple_Disease_Model_best.keras",
    "apple_final": MODELS_DIR / "Apple_Disease_Model_final.keras", 
    "plm_h5": MODELS_DIR / "plm.h5",
    "plm_keras": MODELS_DIR / "plm.keras",
    "strawberry": MODELS_DIR / "Strawberry_Disease_Model_best.keras",
    "tomato": MODELS_DIR / "Tomato_Disease_Model_best.keras",
    "tomato_final": MODELS_DIR / "Tomato_Disease_Model_final.keras"
}

# Disease class mappings for different models
DISEASE_CLASSES = {
    "apple": [
        "Apple___Apple_scab",
        "Apple___Black_rot", 
        "Apple___Cedar_apple_rust",
        "Apple___healthy"
    ],
    "strawberry": [
        "Strawberry___Leaf_scorch",
        "Strawberry___healthy"
    ],
    "tomato": [
        "Tomato___Bacterial_spot",
        "Tomato___Early_blight",
        "Tomato___Late_blight", 
        "Tomato___Leaf_Mold",
        "Tomato___Septoria_leaf_spot",
        "Tomato___Spider_mites Two-spotted_spider_mite",
        "Tomato___Target_Spot",
        "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
        "Tomato___Tomato_mosaic_virus",
        "Tomato___healthy"
    ],
    "general": [
        "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
        "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)___Common_rust_", 
        "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy", "Grape___Black_rot",
        "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
        "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot", "Peach___healthy",
        "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy", "Potato___Early_blight",
        "Potato___Late_blight", "Potato___healthy", "Raspberry___healthy", "Soybean___healthy",
        "Squash___Powdery_mildew", "Strawberry___Leaf_scorch", "Strawberry___healthy",
        "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight", 
        "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot", 
        "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
        "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus", "Tomato___healthy"
    ]
}

# Loaded models cache
_loaded_models = {}

def base64_image_to_file(base64_string: str, output_filepath: str) -> bool:
    """
    Converts a Base64 encoded image string to an image file.
    
    Args:
        base64_string (str): The Base64 encoded image string
        output_filepath (str): The path and filename for the output image file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Remove data URL prefix if present
        if base64_string.startswith("data:"):
            match = re.match(r"data:image/(?P<extension>\w+);base64,(?P<data>.+)", base64_string)
            if match:
                base64_data = match.group("data")
            else:
                logger.error("Invalid data URL format")
                return False
        else:
            base64_data = base64_string
            
        # Decode and save
        decoded_image_data = base64.b64decode(base64_data)
        with open(output_filepath, "wb") as f:
            f.write(decoded_image_data)
            
        logger.info(f"Image successfully saved to {output_filepath}")
        return True
        
    except base64.binascii.Error as e:
        logger.error(f"Error decoding Base64 string: {e}")
        return False
    except IOError as e:
        logger.error(f"Error saving file: {e}")
        return False

def load_model(model_name: str) -> Optional[tf.keras.Model]:
    """
    Load a Keras model with caching.
    
    Args:
        model_name (str): Name of the model to load
        
    Returns:
        tf.keras.Model or None: Loaded model or None if failed
    """
    if model_name in _loaded_models:
        return _loaded_models[model_name]
        
    model_path = MODEL_PATHS.get(model_name)
    if not model_path or not model_path.exists():
        logger.error(f"Model not found: {model_path}")
        return None
        
    try:
        model = tf.keras.models.load_model(model_path)
        _loaded_models[model_name] = model
        logger.info(f"Model loaded successfully: {model_name}")
        return model
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        return None

def preprocess_image(image_path: str, target_size: tuple = (224, 224)) -> Optional[np.ndarray]:
    """
    Preprocess image for model prediction.
    
    Args:
        image_path (str): Path to the image file
        target_size (tuple): Target size for resizing
        
    Returns:
        np.ndarray or None: Preprocessed image array or None if failed
    """
    try:
        image = Image.open(image_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Resize image
        image = image.resize(target_size)
        
        # Convert to array and normalize
        image_array = np.array(image)
        image_array = image_array / 255.0  # Normalize to [0,1]
        
        # Add batch dimension
        image_array = np.expand_dims(image_array, axis=0)
        
        return image_array
        
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        return None

def predict_disease(model: tf.keras.Model, image_array: np.ndarray, class_names: list) -> Dict[str, Any]:
    """
    Make disease prediction using the model.
    
    Args:
        model: Loaded Keras model
        image_array: Preprocessed image array
        class_names: List of class names for the model
        
    Returns:
        Dict containing prediction results
    """
    try:
        predictions = model.predict(image_array)
        predicted_class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_idx])
        predicted_class = class_names[predicted_class_idx]
        
        # Get top 3 predictions
        top_3_idx = np.argsort(predictions[0])[-3:][::-1]
        top_3_predictions = [
            {
                "class": class_names[idx],
                "confidence": float(predictions[0][idx])
            }
            for idx in top_3_idx
        ]
        
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "top_3_predictions": top_3_predictions
        }
        
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        return {"error": str(e)}

def analyze_plant_image(base64_image: str, model_name: str = "general") -> Dict[str, Any]:
    """
    Analyze plant image for disease detection.
    
    Args:
        base64_image (str): Base64 encoded image
        model_name (str): Name of the model to use
        
    Returns:
        Dict containing analysis results
    """
    try:
        # Generate unique filename
        import time
        timestamp = int(time.time())
        image_filename = f"plant_image_{timestamp}.jpg"
        image_path = UPLOADS_DIR / image_filename
        
        # Save base64 image to file
        if not base64_image_to_file(base64_image, str(image_path)):
            return {"error": "Failed to save image file"}
        
        # Determine which model to use based on model_name or try to auto-detect
        model_to_use = model_name
        if model_name == "auto":
            # For auto detection, start with general model
            model_to_use = "plm_keras"  # Use the general plant model
        
        # Load model
        model = load_model(model_to_use)
        if model is None:
            # Fallback to general model
            model_to_use = "plm_keras"
            model = load_model(model_to_use)
            
        if model is None:
            return {"error": f"Could not load any model for analysis"}
        
        # Preprocess image
        image_array = preprocess_image(str(image_path))
        if image_array is None:
            return {"error": "Failed to preprocess image"}
        
        # Get appropriate class names
        if model_to_use in ["plm_keras", "plm_h5"]:
            class_names = DISEASE_CLASSES["general"]
        else:
            # Extract crop name from model name
            for crop in ["apple", "strawberry", "tomato"]:
                if crop in model_to_use:
                    class_names = DISEASE_CLASSES[crop]
                    break
            else:
                class_names = DISEASE_CLASSES["general"]
        
        # Make prediction
        results = predict_disease(model, image_array, class_names)
        
        # Add metadata
        results["model_used"] = model_to_use
        results["image_path"] = str(image_path)
        results["timestamp"] = timestamp
        
        # Clean up the image file (optional, comment out if you want to keep images)
        # os.remove(image_path)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in plant image analysis: {e}")
        return {"error": str(e)}

@tool
def plant_analysis_tool(input_data: str) -> str:
    """
    Analyze plant images for disease detection using trained Keras models.
    
    Args:
        input_data (str): JSON string containing 'image_data' (base64) and optionally 'model_name'
                         Format: '{"image_data": "base64_string", "model_name": "auto"}'
                         Or just the base64 string directly for backward compatibility
        
    Returns:
        str: Analysis results as formatted text
    """
    try:
        import json
        
        # Try to parse as JSON first
        try:
            data = json.loads(input_data)
            image_data = data.get("image_data", "")
            model_name = data.get("model_name", "auto")
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat input_data as direct base64 image data
            image_data = input_data
            model_name = "auto"
        
        if not image_data:
            return "Error: No image data provided"
            
        results = analyze_plant_image(image_data, model_name)
        
        if "error" in results:
            return f"Error analyzing image: {results['error']}"
        
        # Format results
        predicted_class = results.get("predicted_class", "Unknown")
        confidence = results.get("confidence", 0)
        model_used = results.get("model_used", "Unknown")
        
        # Parse disease name for better readability
        disease_name = predicted_class.replace("___", " - ").replace("_", " ")
        
        response = f"🌱 **Plant Disease Analysis Results**\n\n"
        response += f"**Primary Diagnosis:** {disease_name}\n"
        response += f"**Confidence:** {confidence:.2%}\n"
        response += f"**Model Used:** {model_used}\n\n"
        
        # Add top 3 predictions
        if "top_3_predictions" in results:
            response += "**Top 3 Possibilities:**\n"
            for i, pred in enumerate(results["top_3_predictions"], 1):
                clean_name = pred["class"].replace("___", " - ").replace("_", " ")
                response += f"{i}. {clean_name}: {pred['confidence']:.2%}\n"
        
        # Add recommendations based on disease
        if "healthy" in predicted_class.lower():
            response += "\n✅ **Good News!** Your plant appears to be healthy!"
        else:
            response += f"\n⚠️ **Disease Detected:** {disease_name}"
            response += f"\n\n**Recommendations:**"
            response += f"\n• Consult with a local agricultural expert for treatment options"
            response += f"\n• Consider applying appropriate fungicides or treatments"
            response += f"\n• Monitor plant closely for spread of disease"
            response += f"\n• Ensure proper plant spacing and ventilation"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in plant analysis tool: {e}")
        return f"Error analyzing plant image: {str(e)}"

@tool
def plant_models_tool(query: str = "") -> str:
    """
    Get information about available plant disease detection models.
    
    Args:
        query (str): Optional query parameter (unused but required for single-input compatibility)
    
    Returns:
        str: Information about available models
    """
    response = "🤖 **Available Plant Disease Detection Models:**\n\n"
    
    for model_name, model_path in MODEL_PATHS.items():
        status = "✅ Available" if model_path.exists() else "❌ Missing"
        response += f"**{model_name}:** {status}\n"
        
        # Add model description
        if "apple" in model_name:
            response += "  - Specialized for apple diseases (scab, black rot, cedar rust)\n"
        elif "tomato" in model_name:
            response += "  - Specialized for tomato diseases (blight, leaf mold, viruses)\n"
        elif "strawberry" in model_name:
            response += "  - Specialized for strawberry diseases (leaf scorch)\n"
        elif "plm" in model_name:
            response += "  - General plant disease model (multiple crops)\n"
        response += "\n"
    
    response += "**Usage:** Send a plant image and specify the model name, or use 'auto' for automatic selection.\n"
    response += "**Supported formats:** JPG, PNG, JPEG images in base64 format"
    
    return response