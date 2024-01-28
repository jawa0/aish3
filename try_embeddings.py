import numpy as np
import time


print('Importing sentence_transformers...')
start_time = time.time()
from sentence_transformers import SentenceTransformer
end_time = time.time()
print(f'Imported sentence_transformers. Took {end_time - start_time:03} seconds.')


def main():
    print('Loading model...')
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('Loaded model')

    memories = [{"info_chunk": "Atoms are made up of a nucleus and surrounding electrons. The nucleus is composed of protons and neutrons. Each proton has electric charge of +1, each electron has electric charge of -1, and neutrons are electrically neutral.",
                 "summary": "Overview of atomic structure detailing the composition and electrical charge of protons, electrons, and neutrons",
                 "keywords": ['atoms', 'nucleus', 'electrons', 'protons', 'neutrons', 'electric charge', '+1', '-1', 'electrically neutral']},
                {"info_chunk": "There are various kinds of chemical bonds, but if not specified or not clear from the context, 'bond' refers to a covalent bond.",
                 "summary": "Understanding that 'bond' typically denotes a covalent bond in an unspecified or unclear chemical context.",
                 "keywords": ["chemical bonds", "covalent bond", "bond", "context", "specified"]},
                {"info_chunk": "In a covalent bond, two atoms share some electrons.",
                 "summary": "Understanding electron sharing in covalent bonds between two atoms.",
                 "keywords": ["covalent bond", "atoms", "share", "electrons"]},
                {"info_chunk": "There are three basic modifications that can be made to a piece of text. (1) Deletion: delete a range of text characters. (2) Insertion: insert new text into some position of the existing text. (3) Substitution: replace a range of characters in the text to be modified with a new sequnce of characters. All transformations to text files can be broken down into combinations of these three basic operations.",
                 "summary": "Overview of the three fundamental text modifications: deletion, insertion, and substitution.",
                 "keywords": ["text modifications", "deletion", "insertion", "substitution", "text characters", "transformations", "text files", "basic operations"]},
                {"info_chunk": "To be electrically neutral, an atom must have a net charge of 0. But all atoms must have a nucleaus with at least one proton. So to balance the charge, the number of protons and neutrons must be equal.",
                 "summary": "Explanation of electrical neutrality in atoms through equal numbers of protons and electrons.",
                 "keywords": ["electrically neutral", "atom", "net charge", "0", "nucleus", "proton", "balance", "number", "protons", "neutrons", "equal"]},
                {"info_chunk": "An ion is an atom or molecule with a non-zero net electrical charge.",
                 "summary": "Explanation of an ion as an atom or molecule that possesses a non-zero net electrical charge",
                 "keywords": ["ion", "atom", "molecule", "electrical charge", "non-zero net charge"]},
                {"info_chunk": "In chemistry, the oxidation state, or oxidation number, is the hypothetical charge of an atom if all of its bonds to other atoms were fully ionic. It describes the degree of oxidation (loss of electrons) of an atom in a chemical compound. Conceptually, the oxidation state may be positive, negative or zero. While fully ionic bonds are not found in nature, many bonds exhibit strong ionicity, making oxidation state a useful predictor of charge. The oxidation state of an atom does not represent the 'real' charge on that atom, or any other actual atomic property. This is particularly true of high oxidation states, where the ionization energy required to produce a multiply positive ion is far greater than the energies available in chemical reactions. Additionally, the oxidation states of atoms in a given compound may vary depending on the choice of electronegativity scale used in their calculation. Thus, the oxidation state of an atom in a compound is purely a formalism. It is nevertheless important in understanding the nomenclature conventions of inorganic compounds. Also, several observations regarding chemical reactions may be explained at a basic level in terms of oxidation states.",
                 "summary": "Explanation of oxidation states in chemistry, their role in predicting charge despite not reflecting actual atomic properties, and significance in inorganic nomenclature and basic chemical reactions.",
                 "keywords": ['chemistry', 'oxidation state', 'oxidation number', 'hypothetical charge', 'ionic bonds', 'degree of oxidation', 'electron loss', 'positive oxidation state', 'negative oxidation state', 'zero oxidation state', 'ionicity', 'predictor of charge', 'real atomic charge', 'ionization energy', 'chemical reactions', 'electronegativity scale', 'formalism', 'inorganic compounds nomenclature', 'chemical reaction explanation']},
                {"info_chunk": "When making modifications to a function definition in program source code, if the function signature is modified, then all call sites need to be examined to make sure that the function calls are compatible with the new signature.",
                 "summary": "Modifying a function's signature in source code necessitates the review of all call sites for compatibility.",
                 "keywords": ['modifications', 'function definition', 'program source code', 'function signature', 'call sites', 'function calls', 'compatibility', 'new signature']},
                {"info_chunk": "When making a modification to program source code, modifying code in one file can cause cascading changes in other files. When considering any code change, it's important to figure out what other code (possibly in other files) will be affected by the change.",
                 "summary": "Understanding the impact of source code modifications on related files in a program.",
                 "keywords": ['modification', 'program source code', 'modifying code', 'cascading changes', 'code change', 'affected']},
    ]

    for memory in memories:
        embeddings = model.encode([memory["summary"]])
        embedding = embeddings[0]
        print(embedding.size)

        norm = np.linalg.norm(embeddings[0])  # normalize for later cosine similarity
        print(norm)

        normalized_embedding = embedding / norm
        print(normalized_embedding.size)

        memory["summary_embedding"] = normalized_embedding

    query_sentences = [
        "what are atoms made of?",
        "I am modifying a text file",
        "I am modifying a program source code file",
        "Electrons are negatively charged",
        "The ion has charge of +1",
        "The magnesium has an oxidation state of +2",
        "By convention, the cathode is positive, so it attracts negatively charged ions, and repels positively charged ions.",
        "We need to modify this code.",
        "We should modify the do_foo() function.",
    ]

    for q in query_sentences:
        q_embedding = model.encode([q])[0]
        q_embedding = q_embedding / np.linalg.norm(q_embedding)

        print(f"QUERY: {q}")
        
        matches = []
        for m in memories:
            m_summary = m["summary"]
            m_embedding = m["summary_embedding"]
            cos_similarity = np.dot(q_embedding, m_embedding)

            matches.append((cos_similarity, m_summary))
        
        # Sort the matches by decreasing cos similarity
        matches = sorted(matches, key=lambda x: x[0], reverse=True)
        for match in matches:
            cos_similarity = match[0]
            if cos_similarity >= 0.1:
                print(f" {cos_similarity:0.6f}: {match[1]}")


if __name__ == "__main__":
    main()