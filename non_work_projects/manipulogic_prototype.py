import re
import itertools

r'''
Proposotional Statement Syntax:
- All variables are one single upper letter, i.e., [A-Z]
- No spaces or other whitespaces are allowed
- Binary Operators:
     & :: conjunction
     + :: dijunction / inclusive or
     ^ :: exclusive or
     = :: biconditional / binary equality
     > :: material implication (i.e., P>Q=~P+Q)
- Unary Operators:
     ~ :: unary negation
- Only round parentheses, (), should be used to override
  operator precedence.  Other bracket types are not allowed.

Examples of well-formed statements:
P>Q
(P>Q)
~(P>Q)+R
P
~~R+(P^~Q)=(P=Q)>R
'''

# The strategy for checking well-formed-ness is to tokenize the
# stringify'd statement and then implement the rules to check for
# syntax erros based on each of the token types.
VARIABLE_PATTERN = r'[A-Z]'  # Matches any single uppercase letter
OPERATOR_PATTERN = r'[&+>^=]'  # Matches any binary logical operator
# Matches any valid token in the inputted statement: a variable, a binary operator, negation, or parens
VALID_PATTERN = rf'{VARIABLE_PATTERN}|{OPERATOR_PATTERN}|[()]|~'


def tokenize(statement):
    # Define the regex patterns for tokens
    return re.findall(VALID_PATTERN, statement)

def is_well_formed(statement):
    # Tokenize the statement
    tokens = tokenize(statement)

    # Check if the concatenated tokens match the original statement
    if ''.join(tokens) != statement or len(tokens) < 1:
        return False
    # Ensure we start with an open parens, a negation, or a varaible
    if not (re.fullmatch(VARIABLE_PATTERN, tokens[0]) or tokens[0] in ('(', '~')):
        return False
    # Ensure we end with closed parens or a variable
    if not (re.fullmatch(VARIABLE_PATTERN, tokens[-1]) or tokens[-1] == ')'):
        return False
        
    # Additional syntactical checks:
    stack = []  # Stack to check balanced parentheses
    last_token = ''  # Track the last token to check token-neighbor relations
    for i, token in enumerate(tokens):
        if token == '(':
            stack.append(token)
        elif token == ')':
            if not stack or last_token == '(':
                return False
            stack.pop()
            # Ensure the next token (if any) is an operator or the end of the statement
            if i + 1 < len(tokens) and tokens[i + 1] not in '&+>^=)':
                return False
        elif token == '~':
            # Negation must be preceded by a binary operator unless it is the first token,
            # double negation, or the negation of a paren'd sub-statement
            if not re.fullmatch(OPERATOR_PATTERN, last_token) and i != 0 and tokens[i+1] != '(' and last_token != '~' and last_token != '(':
                return False
        elif re.fullmatch(VARIABLE_PATTERN, token):
            if re.fullmatch(VARIABLE_PATTERN, last_token) or last_token == ')':
                return False
        elif re.fullmatch(OPERATOR_PATTERN, token):
            if re.fullmatch(OPERATOR_PATTERN, last_token) or last_token == '(':
                return False
        last_token = token
    # Ensure all opened parentheses are closed
    if stack:
        return False
        
    return True

# I tried to find a way to do this without converting to postfix notation,
# but nothing worked as well as this.
def evaluate_statement(statement, truth_values):
    def eval_tokens(tokens):
        stack = []
        for token in tokens:
            if token in truth_values:
                stack.append(truth_values[token])
            elif token == '~':
                stack.append(not stack.pop())
            elif token in ('&', '+', '>', '^', '='):
                b = stack.pop()
                a = stack.pop()
                if token == '&':
                    stack.append(a and b)
                elif token == '+':
                    stack.append(a or b)
                elif token == '>':
                    stack.append(not a or b)
                elif token == '^':
                    stack.append(a != b)
                elif token == '=':
                    stack.append(a == b)
        return stack.pop()
    
    tokens = tokenize(statement)
    output = []
    operators = []
    precedence = {'~': 3, '&': 2, '+': 1, '>': 0, '^': 0, '=': 0, '(': -1, ')': -1}
    
    for token in tokens:
        if re.fullmatch(r'[A-Z]', token):
            output.append(token)
        elif token == '(':
            operators.append(token)
        elif token == ')':
            while operators and operators[-1] != '(':
                output.append(operators.pop())
            operators.pop()
        else:
            while (operators and 
                   precedence[operators[-1]] >= precedence[token]):
                output.append(operators.pop())
            operators.append(token)
    
    while operators:
        output.append(operators.pop())
    
    return eval_tokens(output)

def generate_truth_table(variables):
    return [dict(zip(variables, values)) for values in itertools.product([True, False], repeat=len(variables))]

def check_validity(premises, conclusion):
    all_statements = premises + [conclusion]
    variables = sorted(set(token for stmt in all_statements for token in tokenize(stmt) if re.fullmatch(r'[A-Z]', token)))
    truth_table = generate_truth_table(variables)
    
    for truth_values in truth_table:
        premises_truth = all(evaluate_statement(p, truth_values) for p in premises)
        conclusion_truth = evaluate_statement(conclusion, truth_values)
        if premises_truth and not conclusion_truth:
            return False
    return True

def check_user_argument(premises, conclusion):
    not_well_formed_premises = ''
    for premise in premises:
        if not is_well_formed(premise):
            not_well_formed_premises += f'Premise {premise} is not well-formed.\n'
    if not_well_formed_premises:
        return False, not_well_formed_premises
    if not is_well_formed(conclusion):
        return False, f'Conclusion {conclusion} is not well-formed.\n'
    argument_valid = check_validity(premises, conclusion)
    return argument_valid, f'The inputted argument is{"" if argument_valid else " not"} valid.'

def start_command_line_mode():
    print('Starting ManipuLogic command line mode.')
    print('''Usage: enter in your premises, then enter in your conclusion.
    Special commands are:
    - exit : exits the program entirely
    - done : stipulates to end the entry of premises.
The script will determine if your argument is logically valid according to classical propositional logic.
''')
    
    in_str = ''
    while True:   
        well_formed_premises = []
        all_premises_well_formed = True
        conclusion = ''
        print('Start entering your premises.\n')
        in_str = input('Enter premise #1 :')
        while in_str not in ('exit', 'done'):
            stripped = in_str.strip()
            if is_well_formed(stripped):
                print(f'Premise {stripped} is well formed.')
                well_formed_premises.append(stripped)
            else:
                print(f'Premise {stripped} is not well formed.  Check your syntax and try again')
                all_premises_well_formed = False
            in_str = input(f'Enter premise #{len(well_formed_premises)+1}: ')
        if not all_premises_well_formed:
            print('Exiting Manipulogic Command line mode')
            return
        if in_str != 'exit':
            in_str = input('Done entering premises.  All premises are well-formed.  Enter your conclusion: ')
            if in_str != 'exit':
                stripped = in_str.strip()
                if is_well_formed(stripped):
                    conclusion = stripped
                else:
                    print(f'Conclusion {stripped} is not well formed.  Check your syntax and try again')
                    in_str = 'exit'
        if in_str != 'exit':
            print(f'***Your argument is {"" if check_user_argument(well_formed_premises, conclusion) else " not"}valid***\n')
            in_str = input('Type "exit" to quit this program or just hit enter to input in another argument.')
        if in_str == 'exit':
            print('Exiting Manipulogic Command line mode')
            return

if __name__ == '__main__':
    start_command_line_mode()



def test_is_well_formed():
    # Test suite in a dictionary
    test_cases = {
        # Valid propositions
        'A': True,
        'A+B': True,
        'A+B&C': True,
        '(A+B)&C': True,
        'A>(B&C)': True,
        'A>(B=C)': True,
        'A>(B>C)': True,
        '~A': True,
        '~(A&B)': True,
        '((A))': True,
        'A+(B&C^D)': True,
        'A>(B>(C>(D)))': True,
        '(A>B)=C': True,
        '~(A+B)': True,
        'A^B&C+D>E': True,
        'A=B=C': True,
        
        # Invalid propositions
        '': False,  # Empty string
        'A+B&': False,  # Ends with an operator
        '&A+B': False,  # Starts with an operator
        'A+(B&C': False,  # Unmatched parentheses
        'A+(B&C))': False,  # Unmatched parentheses
        'A~B': False,  # Misplaced negation
        'A++B': False,  # Consecutive operators
        'A B': False,  # Missing operator
        'A+': False,  # Ends with operator
        '(A+B))': False,  # Unmatched parentheses
        '(A+B)(C+D)': False,  # Missing operator between sub-expressions
        '~~A': True,  # Valid double negation
        'A+~B': True,  # Negation before variable
        '(A+~B)': True,  # Negation within parentheses
        'A>(B+C)=D': True,  # Mixed operators
        'A>>B': False,  # Double implication
        'A=>(B+C)': False,  # Invalid combination of operators
        'A&(B)': True,  # Valid use of parentheses
        '~(A)': True,  # Valid negation with parentheses
        'A+B C': False,  # Missing operator between variables
        'A&~': False,  # Ends with negation
    }
    for premise, expected in test_cases.items():
        result = is_well_formed(premise)
        assert result == expected, f"Test failed for premise '{premise}'. Expected {expected} but got {result}."
    print("All tests passed.")