from FDM_predictive_detector import PredictiveTimingDetector

if __name__ == "__main__":
    # Default region matches your original script
    detector = PredictiveTimingDetector(527, 196, 1374, 916)
    detector.run()
