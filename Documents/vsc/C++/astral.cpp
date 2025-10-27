#include <iostream>
#include <vector>
#include <string>
#include <set>

using namespace std;

bool isValid(int x, int y, int n) {
    return x >= 0 && x < n && y >= 0 && y < n;
}

int solve(int n, int a, int b, vector<string>& photo) {
    int stars = 0;
    vector<vector<bool> > used(n, vector<bool>(n, false));
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (photo[i][j] == 'B') {
                int prev_i = i - b;
                int prev_j = j - a;
                if (!isValid(prev_i, prev_j, n) || photo[prev_i][prev_j] == 'W') {
                    return -1;
                }
                used[prev_i][prev_j] = true;
                stars++;
            }
        }
    }
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (photo[i][j] == 'G') {
                int prev_i = i - b;
                int prev_j = j - a;
                
                if (isValid(prev_i, prev_j, n) && !used[prev_i][prev_j]) {
                    used[prev_i][prev_j] = true;
                    stars++;
                }
                else if (!used[i][j]) {
                    used[i][j] = true;
                    stars++;
                }
            }
        }
    }
    return stars;
}

int main() {
    int t;
    cin >> t;
    
    while (t--) {
        int n, a, b;
        cin >> n >> a >> b;
        
        vector<string> photo(n);
        for (int i = 0; i < n; i++) {
            cin >> photo[i];
        }
        
        cout << solve(n, a, b, photo) << endl;
    }
    return 0;
}