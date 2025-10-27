#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    vector<int> freq(n + 1, 0);
    for (int i = 0; i < n; i++) {
        if (a[i] <= n) {
            freq[a[i]]++;
        }
    }
    
    vector<bool> present(n + 1, false);
    for (int i = 0; i <= n; i++) {
        if (freq[i] > 0) {
            present[i] = true;
        }
    }
    
    vector<int> miss(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        miss[i] = miss[i-1] + (present[i-1] ? 0 : 1);
    }
    
    for (int mex = 0; mex <= n; mex++) {
        int missing = miss[mex];
        
        int equal_mex = freq[mex];
        
        cout << max(missing, equal_mex) << endl;
    }
    
    return 0;
}