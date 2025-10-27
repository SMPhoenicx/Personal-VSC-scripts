/*
ID: sumanm
LANG: C++
TASK: skidesign
*/
#include <iostream>
#include <fstream>
#include <string.h>
using namespace std;

int main(){
	ofstream fout ("skidesign.out");
    ifstream fin ("skidesign.in");

    int n;
    int l;
    int s;
    fin>>n;
    int cur;
    fin>>l;
    fin>>s;
    if(s > l){
        int temp = s;
        s = l;
        l = temp;
    }
    for(int i = 0; i < n - 2; i++)
    {
        fin>>cur;
        if(cur > l) l = cur;
        if(cur < s) s = cur;
    }
    if((l-s) < 17) fout<<0<<endl;
    int diff = (l-s-17)/2;
    int final = ((l-s-17)%2 == 0) ? 2*(diff*diff): ((diff*diff) + (diff+1)*(diff+1));
    fout<<final<<endl;
}