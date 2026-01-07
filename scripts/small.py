#PatternCount

def PatternCount(Text, Pattern):
    count = 0
    for i in range(len(Text)-len(Pattern)+1):
        if Text[i:i+len(Pattern)] == Pattern:
            count = count+1
    return count 

Text ="GATCCAGATCCCCATAC"
Pattern = "ATA"

print(PatternCount(Text, Pattern))

#FrequencyMap

def FrequentWords(Text, k):
    words = []
    freq = FrequencyMap(Text, k)
    m = max(freq.values())
    for key, value in freq.items():
        if value == m:
         words.append(key)
    return words   

def FrequencyMap(Text, k):
    freq = {}
    for i in range(len(Text) - k + 1):
        pattern = Text[i:i+k]
        freq[pattern] = freq.get(pattern, 0) + 1
    return freq

Text = "atcaatgattatttcatatttcatattt"
k = 9

print(FrequentWords(Text, k))

#ReverseComplement

def ReverseComplement(Pattern):

    trans_table = str.maketrans("ATCG", "TAGC")
    complement = Pattern.upper().translate(trans_table)
    
    return complement[::-1]

dna = "AAAACCCGGT"
print(f"Original: {dna}")
print(f"RevComp:  {ReverseComplement(dna)}")

#PatternMatching

def PatternMatching(Pattern, Genome):
    positions = [] 
    k = len(Pattern)
  
    for i in range(len(Genome) - k + 1):
        if Genome[i:i + k] == Pattern.upper():
            positions.append(i)
    return positions

Genome = "CTGCGATGTTTGGTGGTCACGCAA"
Pattern = "CTTGATCAT"

positions = PatternMatching(Pattern, Genome)
print(f"Pattern found at indices: {positions}")
