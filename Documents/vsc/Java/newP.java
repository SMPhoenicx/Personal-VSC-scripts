package Java;
public class newP {
    static int[][] arr = new int[10][10];
    public static void main(String[] args) {
        Spiral(1, 10);
        for(int x[]:arr)
        {
            for(int y:x)
            {
                System.out.print(y+" ");
            }
            System.out.println();
        }
    }
    public static void Spiral(int X, int Y){
        int x,y,dx,dy;
        x = y = dx =0;
        dy = -1;
        int t = Integer.max(X,Y);
        int maxI = t*t;
        for(int i =0; i < maxI; i++){
            if ((-X/2 <= x) && (x <= X/2) && (-Y/2 <= y) && (y <= Y/2)){
                arr[x][y] = 10;
            }
            if( (x == y) || ((x < 0) && (x == -y)) || ((x > 0) && (x == 1-y))){
                t = dx;
                dx = -dy;
                dy = t;
            }
            x += dx;
            y += dy;
        }
    }
}
