#include <iostream>
#include <string>
#include <algorithm>
#include <vector>
using namespace std;

int main()
{
    int n, q;
    cin>>n>>q;
    vector<int> close;
    vector<int> time;
    for(int i = 0; i < n; i++)
    {
        int c;
        cin>>c;
        close.push_back(c);
    }
    for(int i = 0; i < n; i++)
    {
        int t;
        cin>>t;
        time.push_back(t);
    }
    for(int i = 0; i < q; i++)
    {
        int d, p;
        cin>>d>>p;
        int total = 0;
        for(int j = 0; j < n; j++)
        {
            if(time[j] + p < close[j]) total++;
        }
        if(total >= d) cout<< "YES"<<endl;
        else cout<<"NO"<<endl;
    }
    return 0;
}