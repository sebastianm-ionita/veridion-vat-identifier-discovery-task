from math import sqrt

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Interval de incredere Wilson 95% pentru k succese din n incercari. L-am folosit pentru ca numerele sunt mici"""
    p = k / n
    d = 1 + z * z / n
    centru = p + z * z / (2 * n)
    latime = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centru - latime) / d * 100, (centru + latime) / d * 100

if __name__ == "__main__":
    for eticheta, k, n in [
        ("A: VAT gasit",        8, 300),
        ("A: false pozitive",   0,   8),
        ("B: publica VAT",      6,  16),
        ("C: inregistrate",   128, 131),
        ("C: atribuire",       36,  48),
        ("C: false pozitive",  12,  48),
    ]:
        jos, sus = wilson(k, n)
        print(f"{eticheta:<20} {k}/{n}  {k/n*100:5.1f}%  CI {jos:.1f} - {sus:.1f}")