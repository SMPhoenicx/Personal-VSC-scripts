#include <iostream>
#include <string>
#include <algorithm>
#include <vector>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        string S;
        cin >> S;
        if (S[S.length() - 1] == '0')
            cout << "E" << endl;
        else
            cout << "B" << endl;
    }
    return 0;
}