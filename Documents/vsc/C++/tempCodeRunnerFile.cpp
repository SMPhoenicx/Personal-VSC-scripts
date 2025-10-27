#include <iostream>
#include <vector>
#include <algorithm>
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
    
    for (int i = 0; i <= n; i++) {
        int ops = 0;
        
        for (int j = 0; j < i; j++) {
            if (freq[j] == 0) {
                ops++; 
            }
        }
        
        ops += freq[i];
        
        cout << ops << endl;
    }
    
    return 0;
}