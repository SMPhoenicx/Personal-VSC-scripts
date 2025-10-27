#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <unordered_map>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    long long n;
    cin >> n;
    vector<int> a(n);
    for(int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    set<pair<int, int> > moos;  
    for(int i = 0; i < n; i++) {
        vector<bool> seen_after(n + 1, false);
        
        for(int j = i + 1; j < n; j++) {
            if(seen_after[a[j]]) {
                if(a[i] != a[j]) {
                    moos.insert(make_pair(a[i], a[j]));
                }
            }
            seen_after[a[j]] = true;
        }
    }
    
    cout << moos.size() << endl;
    return 0;
}