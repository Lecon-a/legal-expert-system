from pyswip import Prolog
import re
import threading

# Global lock for thread safety
_prolog_lock = threading.Lock()

# Load rules once
_prolog = Prolog()
_prolog.consult("prolog/legal_rules.pl")

def classify_with_prolog(text):
    """
    Classifies a document using Prolog rules.
    Returns the actual category string like 'contract', 'nda', 'loan', etc.
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())

    with _prolog_lock:
        # Clear previous facts
        _prolog.retractall("contains(_)")

        # Assert new words
        for w in words:
            _prolog.assertz(f"contains('{w}')")

        # Query best_category
        result = list(_prolog.query("best_category(X)"))

        # Clean up facts
        _prolog.retractall("contains(_)")

    print("Before condition block ::: Prolog query result:", result)
    if result and 'X' in result[0]:
        print("Prolog classification successful.")
        print("Prolog result:", result)
        print(f"Prolog classified as: {result[0]['X']}")
        # Ensure we get the atom name, not internal reference
        return str(result[0]['X'])
    print("Prolog classification failed, returning 'Unknown'")
    return "Unknown"