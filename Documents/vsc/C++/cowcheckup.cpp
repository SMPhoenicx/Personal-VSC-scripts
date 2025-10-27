#include <iostream>
#include <vector>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    cin >> n;
    vector<int> a(n);
    vector<int> b(n);
    vector<long long> nums(n + 1, 0);
    
    for(int i = 0; i < n; i++) cin >> a[i];
    for(int i = 0; i < n; i++) cin >> b[i];
    
    vector<bool> matches(n);
    int initial_matches = 0;
    for(int i = 0; i < n; i++) {
        matches[i] = (a[i] == b[i]);
        if(matches[i]) initial_matches++;
    }
    
    for(int l = 0; l < n; l++) {
        int curr_matches = initial_matches;
        
        for(int i = l; i < n; i++) {
            if(matches[i]) curr_matches--;
        }
        
        for(int r = l; r < n; r++) {
            int i = l, j = r;
            int temp_matches = curr_matches;
            
            while(i <= j) {
                if(a[j] == b[i]) temp_matches++;
                
                if(i != j && a[i] == b[j]) temp_matches++;
                
                i++;
                j--;
            }
            
            nums[temp_matches]++;
        }
    }
    
    for(int i = 0; i <= n; i++) {
        cout << nums[i] << "\n";
    }
    
    return 0;
}