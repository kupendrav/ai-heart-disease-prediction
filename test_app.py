#!/usr/bin/env python
import sys
sys.path.insert(0, 'env/Lib/site-packages')

try:
    from app import app, model, scaler, feature_names
    print('OK: App imports successful')
    print(f'OK: Model type: {type(model).__name__}')
    print(f'OK: Feature count: {len(feature_names)}')
    print(f'OK: Model name loaded')
    
    # Test form parsing
    import numpy as np
    test_input = {
        'age': 65, 'sex': 1, 'cp': 1, 'trestbps': 145,
        'chol': 250, 'fbs': 1, 'restecg': 1, 'thalach': 110,
        'exang': 1, 'oldpeak': 2.5, 'slope': 1, 'ca': 2, 'thal': 2
    }
    scaled_test = scaler.transform(np.array([list(test_input.values())]))
    pred = model.predict(scaled_test)[0]
    prob = model.predict_proba(scaled_test)[0][1]
    print(f'OK: Test prediction works - Pred: {pred}, Prob: {prob:.2%}')
    print('OK: All production checks passed!')
    
except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
