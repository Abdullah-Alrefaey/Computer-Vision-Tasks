import glob
import math

import cv2
import numpy as np
from sklearn import preprocessing


class FaceRecognizer:
    def __init__(self, path):
        self.dataset_path = path                     # path to the dataset
        self.total_images = 0                        # Total number of images
        self.classes_num = 0                         # Number of classes in each folder
        self.img_shape = (112, 92)                   # size of the dataset images (Fixed)
        self.all_images = None                       # Matrix of all images data
        self.names = list()                          # Save Dataset Classes names
        self.mean_vector = None                      # Mean Vector of A Matrix
        self.A_tilde = None                          # A_tilda Matrix
        self.eigenfaces = None                       # EigenFaces Matrix
        self.eigenfaces_num = 350                    # number of chosen eigenfaces

    def create_images_matrix(self) -> tuple:
        """

        :return:
        """

        for images in glob.glob(self.dataset_path + '/**', recursive=True):
            if images[-3:] == 'pgm' or images[-3:] == 'jpg':
                self.total_images += 1

        # initialize the numpy array
        self.all_images = np.zeros((self.total_images, self.img_shape[0], self.img_shape[1]), dtype='float64')
        i = 0

        # iterate through all the class
        for folder in glob.glob(self.dataset_path + '/*'):
            self.classes_num += 1

            # makes 10 copy of each class name in the list (since we have 10 images in each class)
            for _ in range(10):
                # list for the classes of the faces
                self.names.append(folder[-3:].replace('/', ''))

            # iterate through each folder (class)
            for image in glob.glob(folder + '/*'):

                # read the image in grayscale
                read_image = cv2.imread(image, cv2.IMREAD_GRAYSCALE)

                # cv2.resize resizes an image into (# column x # height)
                resized_image = cv2.resize(read_image, (self.img_shape[1], self.img_shape[0]))
                self.all_images[i] = np.array(resized_image)
                i += 1

        return self.classes_num, self.total_images, self.img_shape

    def fit(self):
        """

        :return:
        """

        # convert the images into vectors. Each row has an image vector. i.e. samples x image_vector matrix
        a = np.resize(self.all_images, (self.total_images, self.img_shape[0] * self.img_shape[1]))

        # calculate the mean vector
        self.mean_vector = np.sum(a, axis=0, dtype='float64') / self.total_images

        # make a 400 copy of the same vector. 400 x image_vector_size matrix.
        mean_matrix = np.tile(self.mean_vector, (self.total_images, 1))

        # mean-subtracted image vectors
        self.A_tilde = a - mean_matrix

        # since each row is an image vector
        # (unlike in the notes, L = (A_tilde)(A_tilde.T) instead of L = (A_tilde.T)(A_tilde)
        L = (self.A_tilde.dot(self.A_tilde.T)) / self.total_images

        # find the eigenvalues and the eigenvectors of L
        eigenvalues, eigenvectors = np.linalg.eig(L)

        # get the indices of the eigenvalues by its value. Descending order.
        idx = eigenvalues.argsort()[::-1]

        # sorted eigenvalues and eigenvectors in descending order
        # eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # linear combination of each column of A_tilde
        eigenvectors_c = self.A_tilde.T @ eigenvectors

        # each column is an eigenvector of C where C = (A_tilde.T)(A_tilde).
        # NOTE : in the notes, C = (A_tilde)(A_tilde.T)

        # normalize the eigenvectors
        # normalize only accepts matrix with n_samples, n_feature. Hence the transpose.
        self.eigenfaces = preprocessing.normalize(eigenvectors_c.T)

        return self.eigenfaces_num

    def detect_face(self, source_path: str) -> bool:
        """

        :param source_path:
        :return:
        """

        found_flag = False          # Flag to check if face is found in the dataset

        # testing image
        test_img = cv2.imread(source_path, cv2.IMREAD_GRAYSCALE)

        # resize the testing image. cv2 resize by width and height.
        test_img = cv2.resize(test_img, (self.img_shape[1], self.img_shape[0]))

        # subtract the mean
        mean_subtracted_test_img = np.reshape(test_img, (test_img.shape[0] * test_img.shape[1])) - self.mean_vector

        # the vector that represents the image with respect to the eigenfaces.
        omega = self.eigenfaces[:self.eigenfaces_num].dot(mean_subtracted_test_img)

        # chosen threshold for face detection
        alpha_1 = 3000

        # n^2 vector of the new face image represented as the linear combination of the chosen eigenfaces
        projected_new_img_vector = self.eigenfaces[:self.eigenfaces_num].T @ omega
        diff = mean_subtracted_test_img - projected_new_img_vector

        # distance between the original face image vector and the projected vector.
        beta = math.sqrt(diff.dot(diff))

        if beta < alpha_1:
            print(f"Face detected in the image!, beta = {beta}")
            found_flag = True
        else:
            print(f"No face detected in the image!, beta = {beta} ")

        return found_flag

    def recognize_face(self, source_path: str) -> str:
        """

        :param source_path:
        :return:
        """

        face_name = "Unknown Face!"

        # Testing image
        test_img = cv2.imread(source_path, cv2.IMREAD_GRAYSCALE)

        # resize the testing image. cv2 resize by width and height.
        test_img = cv2.resize(test_img, (self.img_shape[1], self.img_shape[0]))

        # subtract the mean
        mean_subtracted_test_img = np.reshape(test_img, (test_img.shape[0] * test_img.shape[1])) - self.mean_vector

        # the vector that represents the image with respect to the eigenfaces.
        omega = self.eigenfaces[:self.eigenfaces_num].dot(mean_subtracted_test_img)

        alpha_2 = 3000              # chosen threshold for face recognition
        smallest_value = None       # to keep track of the smallest value
        index = None                # to keep track of the class that produces the smallest value

        for k in range(self.total_images):
            # calculate the vectors of the images in the dataset and represent
            omega_k = self.eigenfaces[:self.eigenfaces_num].dot(self.A_tilde[k])
            diff = omega - omega_k
            epsilon_k = math.sqrt(diff.dot(diff))

            if smallest_value is None:
                smallest_value = epsilon_k
                index = k

            if smallest_value > epsilon_k:
                smallest_value = epsilon_k
                index = k

        if smallest_value < alpha_2:
            face_name = self.names[index]
        else:
            print(f"smallest_value = {smallest_value}, 'Unknown Face!'")

        return face_name


if __name__ == "__main__":

    # image_path = "../resources/Images/faces/right_test.png"
    image_path = "../resources/Images/faces/wrong_test.jpeg"
    recognizer = FaceRecognizer(path="")
    recognizer.fit()
    recognized_name = recognizer.recognize_face(source_path=image_path)
    print(f"recognized_name: {recognized_name}")
