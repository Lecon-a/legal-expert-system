:- dynamic contains/1.

% CONTRACT
keyword(contract, agreement).
keyword(contract, party).
keyword(contract, obligation).
keyword(contract, clause).

% NDA
keyword(nda, confidential).
keyword(nda, disclosure).
keyword(nda, secrecy).

% LOAN
keyword(loan, borrower).
keyword(loan, lender).
keyword(loan, repayment).

% RENTAL
keyword(rental, tenant).
keyword(rental, landlord).
keyword(rental, rent).

score(Category, Score) :-
    findall(Word, (keyword(Category, Word), contains(Word)), Matches),
    length(Matches, Score).

best_category(CategoryAtom) :-
    findall(Score-C, score(C, Score), Scores),
    sort(Scores, Sorted),
    reverse(Sorted, [BestScore-Category|_]),
    BestScore > 0,
    % Only convert to string if Category is instantiated
    nonvar(Category),
    atom_string(CategoryAtom, Category).

% If no category matches, return 'unknown'
best_category('unknown') :-
    \+ best_category(_).