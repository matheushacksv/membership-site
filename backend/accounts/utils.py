"""CPF: normalização + validação de dígitos verificadores.

Path sensível (documento do aluno impresso no certificado) → deixa 1 self-check no __main__.
"""


def normalize_cpf(value: str | None) -> str:
    return ''.join(c for c in (value or '') if c.isdigit())


def validate_cpf(value: str | None) -> bool:
    cpf = normalize_cpf(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:  # 11 dígitos e não todos iguais (111...)
        return False
    for i in (9, 10):  # os 2 dígitos verificadores
        s = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        if (s * 10) % 11 % 10 != int(cpf[i]):
            return False
    return True


if __name__ == '__main__':
    assert validate_cpf('529.982.247-25')       # válido conhecido
    assert validate_cpf('52998224725')
    assert not validate_cpf('111.111.111-11')    # repetido
    assert not validate_cpf('529.982.247-24')    # dígito errado
    assert not validate_cpf('123')               # curto
    assert not validate_cpf('')
    assert normalize_cpf('529.982.247-25') == '52998224725'
    print('ok')
